import json

import aiokafka
import structlog
from aiokafka.helpers import create_ssl_context
from aiokafka.structs import ConsumerRecord
from fhir.resources.bundle import Bundle
from fhir.resources.documentreference import DocumentReference

from ahd2fhir import config
from ahd2fhir.utils.resource_handler import ResourceHandler, TransientError

logger = structlog.get_logger()

consumer_task = None
consumer = None
producer = None

resource_handler: ResourceHandler = None


async def initialize_kafka(handler: ResourceHandler):  # pragma: no cover
    settings = config.Settings()

    global resource_handler
    resource_handler = handler

    ssl_context = None
    if settings.security_protocol != "PLAINTEXT":
        ssl_context = create_ssl_context(
            # CA used to sign certificate.
            cafile=settings.kafka_ssl_cafile,
            # Signed certificate
            certfile=settings.kafka_ssl_certfile,
            # Private Key file of `certfile` certificate
            keyfile=settings.kafka_ssl_keyfile,
        )

    group_id = settings.group_id
    logger.info(
        "Initializing Kafka",
        input_topic=settings.kafka_input_topic,
        group_id=group_id,
        bootstrap_servers=settings.bootstrap_servers,
    )

    global consumer
    # TODO: could this setup be made cleaner by binding the settings.kafka_* to
    #       AIOKafkaConsumer's ctor args? So kafka_max_poll_records gets automatically
    #       turned into max_poll_records.
    consumer = aiokafka.AIOKafkaConsumer(
        settings.kafka_input_topic,
        bootstrap_servers=settings.bootstrap_servers,
        auto_offset_reset=settings.kafka_auto_offset_reset,
        group_id=group_id,
        max_poll_interval_ms=settings.kafka_max_poll_interval_ms,  # 600 s = 10 min
        max_poll_records=settings.kafka_max_poll_records,
        security_protocol=settings.security_protocol,
        ssl_context=ssl_context,
        max_partition_fetch_bytes=settings.kafka_max_message_size_bytes,
        auto_commit_interval_ms=settings.kafka_auto_commit_interval_ms,
        session_timeout_ms=settings.kafka_session_timeout_ms,
        heartbeat_interval_ms=settings.kafka_heartbeat_interval_ms,
    )

    global producer
    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=settings.bootstrap_servers,
        compression_type=settings.kafka_compression_type,
        security_protocol=settings.security_protocol,
        ssl_context=ssl_context,
        max_request_size=settings.kafka_max_message_size_bytes,
    )

    # get cluster layout and join group
    await consumer.start()
    await producer.start()


async def send_consumer_message(consumer):  # pragma: no cover
    settings = config.Settings()

    failed_topic = f"error.{settings.kafka_input_topic}.{settings.group_id}"

    # consume messages
    msg: ConsumerRecord
    async for msg in consumer:
        try:
            resource_json = json.loads(msg.value)
            resource = None
            result: Bundle = None
            if resource_json["resourceType"] == "DocumentReference":
                resource = DocumentReference.parse_raw(msg.value)
                result = resource_handler.handle_documents([resource])
            elif resource_json["resourceType"] == "Bundle":
                resource = Bundle.parse_raw(msg.value)
                result = resource_handler.handle_bundle(resource)
            else:
                raise ValueError(
                    f"Unprocessable resource type '{resource_json['resourceType']}'"
                )

            await producer.send_and_wait(
                settings.kafka_output_topic,
                result.json().encode("utf8"),
                result.id.encode("utf8"),
            )
        except TransientError as exc:
            logger.exception(exc)
            logger.error(
                "Message processing failed with a transient error. "
                + "AHD is most likely down. Stopping consumer entirely."
                + "Please restart it manually."
            )
            # will leave consumer group; perform autocommit if enabled
            await consumer.stop()
            return
        except Exception as exc:
            logger.exception(exc)
            logger.error(
                f"Mapping payload failed: {exc}. Storing in error topic",
                failed_topic=failed_topic,
            )

            headers = [("error", f"Mapping Error: {exc}".encode("utf8"))]

            try:
                await producer.send_and_wait(
                    failed_topic, msg.value, key=msg.key, headers=headers
                )
            except Exception as error_topic_exc:
                logger.error(
                    f"Failed to send message to error topic: {error_topic_exc}"
                )
                logger.exception(error_topic_exc)


async def kafka_start_consuming(resource_handler: ResourceHandler):
    await initialize_kafka(resource_handler)
    return await send_consumer_message(consumer)


async def kafka_stop_consuming():
    logger.info("Stopping Kafka consumer")
    await consumer.stop()
    return await producer.stop()
