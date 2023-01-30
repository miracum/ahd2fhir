import base64
import datetime
import json
import logging
import os

import pytest
import requests
from fhirclient import server
from fhir.resources.bundle import Bundle
from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.fhirtypes import DateTime
from fhir.resources.reference import Reference
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from confluent_kafka import Producer
from confluent_kafka import Consumer

LOG = logging.getLogger(__name__)

AHD2FHIR_API_BASE_URL = os.environ.get("AHD2FHIR_API_BASE_URL", "http://localhost:8080")
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


@pytest.fixture(scope="session", autouse=True)
def wait_for_server_to_be_up():
    session = requests.Session()
    retries = Retry(total=15, backoff_factor=5, status_forcelist=[502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retries))

    LOG.info(f"Using AHD2FHIR service @ {AHD2FHIR_API_BASE_URL}")

    response = session.get(
        f"{AHD2FHIR_API_BASE_URL}/ready",
    )

    if response.status_code != 200:
        pytest.fail("Failed to wait for server to be up")


@pytest.fixture
def fhir_server():
    smart = server.FHIRServer(None, f"{AHD2FHIR_API_BASE_URL}/fhir")
    return smart


def get_test_document_reference():

    text = "Diabetes"

    attachment = Attachment.construct()
    attachment.language = "en"
    attachment.contentType = "text/plain"
    attachment.data = base64.b64encode(text.encode("utf8"))

    content = DocumentReferenceContent.construct()
    content.attachment = attachment

    subject = Reference.construct()
    subject.reference = "Patient/p1"
    subject.type = "Patient"

    doc_ref = DocumentReference.construct()
    doc_ref.status = "current"
    doc_ref.content = [content]
    doc_ref.date = DateTime.validate(datetime.datetime.now(datetime.timezone.utc))
    doc_ref.subject = subject
    doc_ref.id = "e2e-test"

    return doc_ref


def test_rest_api_response_contains_expected_resources(fhir_server: server.FHIRServer):
    document = get_test_document_reference()
    document_dict = json.loads(document.json())

    response = fhir_server.post_json("$analyze-document", resource_json=document_dict)
    response.raise_for_status()

    bundle = Bundle.parse_raw(response.content)

    assert len(bundle.entry) > 0


def test_sending_document_via_kafka_returns_response_bundle():
    p = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    c = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "ahd2fhir-e2e-test",
            "auto.offset.reset": "earliest",
        }
    )

    document = get_test_document_reference()

    p.produce(
        "fhir.documents", document.json().encode("utf8"), document.id.encode("utf8")
    )
    p.flush()

    c.subscribe(["fhir.nlp-results"])

    remaining_retries = 10
    while True:
        msg = c.poll(5.0)

        if msg is None and remaining_retries > 0:
            remaining_retries = remaining_retries - 1
            continue
        if msg.error():
            LOG.error("Consumer error: {}".format(msg.error()))
            continue

        LOG.info("Received message: {}".format(msg.value().decode("utf-8")))

        assert msg is not None

        break

    c.close()
