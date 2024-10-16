import base64
import json

import pytest
from fhir.resources.R4B.attachment import Attachment
from fhir.resources.R4B.bundle import Bundle, BundleEntry
from fhir.resources.R4B.composition import Composition
from fhir.resources.R4B.documentreference import DocumentReferenceContent
from fhir.resources.R4B.fhirtypes import DateTime
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

from ahd2fhir.utils.resource_handler import ResourceHandler
from tests.utils import get_empty_document_reference


class FHIRExtension(SingleFileSnapshotExtension):
    _file_extension = "fhir.json"
    _write_mode = WriteMode.TEXT

    @classmethod
    def get_snapshot_name(cls, *, test_location, index) -> str:
        original_name = SingleFileSnapshotExtension.get_snapshot_name(
            test_location=test_location, index=index
        )
        return original_name


@pytest.fixture
def snapshot_fhir(snapshot):
    return snapshot.use_extension(FHIRExtension)


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


def test_handle_bundle_with_empty_bundle_should_return_empty_result():
    bundle = Bundle(**{"id": "test", "type": "transaction", "entry": []})
    resource_handler = ResourceHandler(averbis_pipeline=MockPipeline())

    bundle = resource_handler.handle_bundle(bundle)

    assert len(bundle.entry) == 0


def test_handle_bundle_with_document_without_content_should_raise_error():
    entry = BundleEntry(**{"resource": get_empty_document_reference()})
    bundle = Bundle(**{"id": "test", "type": "transaction", "entry": [entry]})
    resource_handler = ResourceHandler(averbis_pipeline=MockPipeline())

    with pytest.raises(ValueError):
        bundle = resource_handler.handle_bundle(bundle)


# TODO: should a document resulting in no annotations
#       create resources within the bundle?
def test_handle_bundle_with_content_should_create_composition():
    doc = get_empty_document_reference()
    doc.content[0] = DocumentReferenceContent(
        **{
            "attachment": Attachment(
                **{
                    "data": base64.b64encode("Diabetes".encode("utf-8")),
                    "contentType": "text/plain",
                    "language": "en",
                }
            )
        }
    )
    entry = BundleEntry(**{"resource": doc})
    bundle = Bundle(**{"id": "test", "type": "transaction", "entry": [entry]})
    resource_handler = ResourceHandler(averbis_pipeline=MockPipeline())

    bundle = resource_handler.handle_bundle(bundle)

    assert any(isinstance(e.resource, Composition) for e in bundle.entry)
    assert len(bundle.entry) == 1


def test_get_fhir_medication_should_only_create_unique_bundle_entries():
    doc = get_empty_document_reference()
    doc.content[0] = DocumentReferenceContent(
        **{
            "attachment": Attachment(
                **{
                    "data": base64.b64encode("test".encode("utf-8")),
                    "contentType": "text/plain",
                    "language": "en",
                }
            )
        }
    )

    ahd_response = []
    with open("tests/resources/ahd/payload_creating_duplicate_medication.json") as file:
        ahd_response = json.load(file)

    resource_handler = ResourceHandler(
        averbis_pipeline=MockPipeline(response=ahd_response)
    )

    bundle = resource_handler.handle_documents([doc])

    full_urls = [entry.fullUrl for entry in bundle.entry]
    unique_full_urls = set(full_urls)

    # if the number of fullUrls in the original list is the same as the one in the
    # set of urls, then the full_urls list only contains distinct items
    assert len(full_urls) == len(unique_full_urls)


@pytest.mark.parametrize(
    "ahd_payload_filename", ["complex-payload.json", "simple-payload.json"]
)
def test_handle_documents_from_ahd_payloads_snapshots(
    ahd_payload_filename, snapshot_fhir
):
    doc = get_empty_document_reference()
    doc.content[0] = DocumentReferenceContent(
        **{
            "attachment": Attachment(
                **{
                    "data": base64.b64encode(
                        "empty because a mocked AHD response is used".encode("utf-8")
                    ),
                    "contentType": "text/plain",
                    "language": "en",
                }
            )
        }
    )
    doc.date = DateTime.validate("2000-01-01T00:00:00+00:00")

    ahd_response = []
    with open(f"tests/resources/ahd/v6/{ahd_payload_filename}") as file:
        ahd_response = json.load(file)

    payload = ahd_response["payload"]

    resource_handler = ResourceHandler(
        averbis_pipeline=MockPipeline(response=payload),
        fixed_composition_datetime=doc.date,
    )

    result_bundle = resource_handler.handle_documents([doc])

    assert result_bundle.json(indent=2, ensure_ascii=False) == snapshot_fhir
