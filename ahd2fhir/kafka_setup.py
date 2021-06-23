import json

import aiokafka
import structlog
from aiokafka.consumer.consumer import AIOKafkaConsumer
from aiokafka.producer.producer import AIOKafkaProducer
from fhir.resources.bundle import Bundle
from fhir.resources.documentreference import DocumentReference

from ahd2fhir import config
from ahd2fhir.utils.resource_handler import ResourceHandler, TransientError

TRANSACTIONAL_ID = "ahd2fhir-txn-id"

logger = structlog.get_logger()

consumer_task = None
consumer: AIOKafkaConsumer = None
producer: AIOKafkaProducer = None

resource_handler: ResourceHandler = None

settings = config.Settings()


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
    await consumer.start()

    global producer
    producer = aiokafka.AIOKafkaProducer(
        **settings.kafka.get_connection_context(),
        **settings.kafka.producer.dict(),
        transactional_id=TRANSACTIONAL_ID,
    )
    await producer.start()


def process_batch(msgs):
    results: list[Bundle] = []
    for msg in msgs:
        result = process_message_from_batch(msg)
        results.append(result)
    return results


async def process_message_from_batch(msg):
    try:
        resource_json = json.loads(msg.value)
        if resource_json["resourceType"] == "DocumentReference":
            resource = DocumentReference.parse_raw(msg.value)
            return resource_handler.handle_documents([resource])
        elif resource_json["resourceType"] == "Bundle":
            resource = Bundle.parse_raw(msg.value)
            return resource_handler.handle_bundle(resource)
        else:
            raise ValueError(
                f"Unprocessable resource type '{resource_json['resourceType']}'"
            )
    except Exception as exc:
        failed_topic = f"error.{settings.kafka_input_topic}.{settings.group_id}"
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
            logger.error(f"Failed to send message to error topic: {error_topic_exc}")
            logger.exception(error_topic_exc)


async def send_consumer_message(consumer):  # pragma: no cover
    try:
        while True:
            msg_batch = await consumer.getmany(
                timeout_ms=settings.kafka_max_poll_interval_ms
            )

            async with producer.transaction():
                commit_offsets = {}
                in_msgs = []
                for tp, msgs in msg_batch.items():
                    in_msgs.extend(msgs)
                    commit_offsets[tp] = msgs[-1].offset + 1

                out_msgs = process_batch(in_msgs)

                for out_bundle in out_msgs:
                    await producer.send(
                        settings.kafka_output_topic,
                        value=out_bundle.json().encode("utf8"),
                        key=out_bundle.id.encode("utf8"),
                    )
                # We commit through the producer because we want the commit
                # to only succeed if the whole transaction is done
                # successfully.
                await producer.send_offsets_to_transaction(
                    commit_offsets, settings.group_id
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


async def kafka_start_consuming(resource_handler: ResourceHandler):
    await initialize_kafka(resource_handler)
    return await send_consumer_message(consumer)


async def kafka_stop_consuming():
    logger.info("Stopping Kafka consumer")
    await consumer.stop()
    return await producer.stop()
