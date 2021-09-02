import pytest
from fastapi.testclient import TestClient
from fhir.resources.bundle import Bundle

from ahd2fhir import main
from ahd2fhir.config import Settings
from tests.utils import get_empty_document_reference


def get_settings_override():
    return Settings(
        ahd_url="localhost",
        ahd_api_token="test",
        ahd_project="test",
        ahd_pipeline="test",
    )


class MockResourceHandler:
    def __init__(self, averbis_pipeline, config):
        self.pipeline = averbis_pipeline
        self.config = config

    def handle_documents(self, document_references) -> Bundle:
        bundle = Bundle.construct()
        bundle.type = "transaction"
        bundle.id = "test"
        bundle.entry = []
        return bundle


def get_resource_handler():
    return MockResourceHandler(None, None)


main.app.dependency_overrides[main.get_settings] = get_settings_override
main.app.dependency_overrides[main.get_resource_handler] = get_resource_handler

client = TestClient(main.app)


@pytest.mark.parametrize("endpoint", ["/live", "/ready"])
def test_health_probes(endpoint: str):
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_analyze_document():
    doc = get_empty_document_reference()
    response = client.post("/fhir/$analyze-document", json=doc.dict())

    assert response.status_code == 200
