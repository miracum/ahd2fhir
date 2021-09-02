import base64
import json

import pytest
from fhir.resources.attachment import Attachment
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.composition import Composition
from fhir.resources.documentreference import DocumentReferenceContent

from ahd2fhir.utils.mapper_handler import MapperHandler
from ahd2fhir.utils.resource_handler import ResourceHandler
from tests.test_main import get_settings_override
from tests.utils import get_empty_document_reference


class MockPipeline:
    def __init__(self, response=None) -> None:
        if response is None:
            self.response = []
        else:
            self.response = response

    def analyse_text(self, text: str, language: str, annotation_types: str):
        return self.response

    def analyse_html(self, text: str, language: str, annotation_types: str):
        return self.response


@pytest.fixture
def resource_handler():
    averbis_pipeline = MockPipeline()
    mapper_handler = MapperHandler(get_settings_override())
    return ResourceHandler(averbis_pipeline, mapper_handler)


@pytest.fixture
def resource_handler_with_mock_response():
    ahd_response = []
    with open("tests/resources/ahd/payload_creating_duplicate_medication.json") as file:
        ahd_response = json.load(file)

    averbis_pipeline = MockPipeline(response=ahd_response)
    mapper_handler = MapperHandler(get_settings_override())

    return ResourceHandler(averbis_pipeline, mapper_handler)


def test_handle_bundle_with_empty_bundle_should_return_empty_result(resource_handler):
    bundle = Bundle(**{"id": "test", "type": "transaction", "entry": []})
    bundle = resource_handler.handle_bundle(bundle)

    assert len(bundle.entry) == 0


def test_handle_bundle_with_document_without_content_should_raise_error(
    resource_handler,
):
    entry = BundleEntry(**{"resource": get_empty_document_reference()})
    bundle = Bundle(**{"id": "test", "type": "transaction", "entry": [entry]})

    with pytest.raises(ValueError):
        bundle = resource_handler.handle_bundle(bundle)


# TODO: should a document resulting in no annotations
#       create resources within the bundle?
def test_handle_bundle_with_content_should_create_composition(resource_handler):
    doc = get_empty_document_reference()
    doc.content[0] = DocumentReferenceContent(
        **{
            "attachment": Attachment(
                **{"data": base64.b64encode("Diabetes".encode("utf-8"))}
            )
        }
    )
    entry = BundleEntry(**{"resource": doc})
    bundle = Bundle(**{"id": "test", "type": "transaction", "entry": [entry]})

    bundle = resource_handler.handle_bundle(bundle)

    assert any(isinstance(e.resource, Composition) for e in bundle.entry)
    assert len(bundle.entry) == 1


def test_get_fhir_medication_should_only_create_unique_bundle_entries(
    resource_handler_with_mock_response,
):
    doc = get_empty_document_reference()
    doc.content[0] = DocumentReferenceContent(
        **{
            "attachment": Attachment(
                **{"data": base64.b64encode("test".encode("utf-8"))}
            )
        }
    )

    bundle = resource_handler_with_mock_response.handle_documents([doc])

    full_urls = [entry.fullUrl for entry in bundle.entry]
    unique_full_urls = set(full_urls)

    # if the number of fullUrls in the original list is the same as the one in the
    # set of urls, then the full_urls list only contains distinct items
    assert len(full_urls) == len(unique_full_urls)
