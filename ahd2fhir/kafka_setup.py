import json

import aiokafka
import structlog
from aiokafka.structs import ConsumerRecord
from fhir.resources.bundle import Bundle
from fhir.resources.documentreference import DocumentReference

from ahd2fhir import config
from ahd2fhir.utils.resource_handler import ResourceHandler, TransientError

logger = structlog.get_logger()

consumer: aiokafka.AIOKafkaConsumer = None
producer: aiokafka.AIOKafkaProducer = None
resource_handler: ResourceHandler | None = None


async def initialize_kafka(handler: ResourceHandler):  # pragma: no cover
    settings = config.Settings()

    global resource_handler
    resource_handler = handler

    group_id = settings.kafka.consumer.group_id

    logger.info(
        "Initializing Kafka",
        input_topic=settings.kafka.input_topic,
        group_id=group_id,
        bootstrap_servers=settings.kafka.bootstrap_servers,
    )

    global consumer

    consumer = aiokafka.AIOKafkaConsumer(
        settings.kafka.input_topic,
        **settings.kafka.get_connection_context(),
        **settings.kafka.consumer.dict(),
    )

    global producer
    producer = aiokafka.AIOKafkaProducer(
        **settings.kafka.get_connection_context(),
        max_request_size=settings.kafka.max_message_size_bytes,
        **settings.kafka.producer.dict(),
    )

    # get cluster layout and join group
    await consumer.start()
    await producer.start()


async def send_consumer_message(consumer):  # pragma: no cover
    settings = config.Settings()

    failed_topic = (
        f"error.{settings.kafka.input_topic}.{settings.kafka.consumer.group_id}"
    )

    if resource_handler is None:
        raise ValueError(
            "resource_handler is unset. Be sure to call initialize_kafka first."
        )

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
                settings.kafka.output_topic,
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
