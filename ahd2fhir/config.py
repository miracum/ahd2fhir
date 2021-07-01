from os import path

from pydantic import BaseSettings

TLS_ROOT_DIR = "/opt/kafka-certs/"


class Settings(BaseSettings):
    # AHD URL. Should not end with a trailing '/'
    ahd_url: str
    # AHD API token
    ahd_api_token: str
    # name of the AHD project
    ahd_project: str
    # name of the pipeline
    ahd_pipeline: str

    # Kafka-related settings
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "PLAINTEXT"
    group_id: str = "ahd2fhir"

    kafka_input_topic: str = "fhir.documents"
    kafka_output_topic: str = "fhir.nlp-results"
    kafka_compression_type: str = "gzip"
    kafka_max_message_size_bytes: int = 5242880  # 5 MiB
    # reduced number of records to poll by default
    # to give AHD enough time to respond
    kafka_max_poll_records: int = 5
    kafka_max_poll_interval_ms: int = 600_000  # 10 minutes
    kafka_ssl_cafile: str = path.join(TLS_ROOT_DIR, "ca.crt")
    kafka_ssl_certfile: str = path.join(TLS_ROOT_DIR, "user.crt")
    kafka_ssl_keyfile: str = path.join(TLS_ROOT_DIR, "user.key")
    kafka_auto_commit_interval_ms: int = 5000
    kafka_session_timeout_ms: int = 15000
    # kafka_sasl_plain_username: str = None
    # kafka_sasl_plain_password: str = None
    # kafka_sasl_mechanism: str = None

    # The value must be set lower than session_timeout_ms,
    # but typically should be set no higher than 1/3 of
    # that value. It can be adjusted even lower to control
    # the expected time for normal rebalances.
    kafka_heartbeat_interval_ms: int = 3000
    kafka_auto_offset_reset: str = "earliest"
