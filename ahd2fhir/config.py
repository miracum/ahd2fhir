from os import path

from aiokafka.helpers import create_ssl_context
from pydantic import BaseSettings, validator

TLS_ROOT_DIR = "/opt/kafka-certs/"

# pylint: disable=E0213


class KafkaConsumerSettings(BaseSettings):
    group_id: str = "ahd2fhir"
    auto_commit_interval_ms: int = 5000
    session_timeout_ms: int = 15000
    # reduced number of records to poll by default
    # to give AHD enough time to respond
    max_poll_records: int = 5
    max_poll_interval_ms: int = 600_000  # 10 minutes
    # The value must be set lower than session_timeout_ms,
    # but typically should be set no higher than 1/3 of
    # that value. It can be adjusted even lower to control
    # the expected time for normal rebalances.
    heartbeat_interval_ms: int = 3000
    auto_offset_reset: str = "earliest"

    class Config:
        env_prefix = "kafka_consumer_"


class KafkaProducerSettings(BaseSettings):
    compression_type: str = "gzip"

    class Config:
        env_prefix = "kafka_producer_"


class KafkaSettings(BaseSettings):
    input_topic: str = "fhir.documents"
    output_topic: str = "fhir.nlp-results"
    consumer = KafkaConsumerSettings()
    producer = KafkaProducerSettings()

    # Kafka-related settings
    bootstrap_servers: str = "localhost:9092"
    max_message_size_bytes: int = 5242880  # 5 MiB

    # SSL Settings
    security_protocol: str = "PLAINTEXT"
    ssl_cafile: str = path.join(TLS_ROOT_DIR, "ca.crt")
    ssl_certfile: str = path.join(TLS_ROOT_DIR, "user.crt")
    ssl_keyfile: str = path.join(TLS_ROOT_DIR, "user.key")
    # SASL Settings
    sasl_mechanism: str = ""
    sasl_plain_username: str = ""
    sasl_plain_password: str = ""

    #  For using SASL without SSL certificates the *file args need to be None.
    # Otherwise AIOKafkaClient will try to parse them even if they
    # consist of an empty string.
    @validator("ssl_cafile", "ssl_certfile", "ssl_keyfile")
    def parse_to_none(cls, v):
        return None if v in ["", "None", 0, False] else v

    def get_connection_context(self):
        return {
            "ssl_context": self.get_ssl_context(),
            "bootstrap_servers": self.bootstrap_servers,
            "security_protocol": self.security_protocol,
            "sasl_plain_username": self.sasl_plain_username,
            "sasl_plain_password": self.sasl_plain_password,
            "sasl_mechanism": self.sasl_mechanism,
        }

    class Config:
        env_prefix = "kafka_"

    def get_ssl_context(self):
        if self.security_protocol != "PLAINTEXT":
            return create_ssl_context(
                # CA used to sign certificate.
                cafile=self.ssl_cafile,
                # Signed certificate
                certfile=self.ssl_certfile,
                # Private Key file of `certfile` certificate
                keyfile=self.ssl_keyfile,
            )
        return None


class Settings(BaseSettings):
    # AHD URL. Should not end with a trailing '/'
    ahd_url: str = ""
    # AHD API token
    ahd_api_token: str = ""
    # name of the AHD project
    ahd_project: str = ""
    # name of the pipeline
    ahd_pipeline: str = ""
    # Kafka Settings
    kafka: KafkaSettings = KafkaSettings()
    # ahd_version
    ahd_version: str = ""
