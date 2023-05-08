import base64
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from fhir.resources.attachment import Attachment
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.composition import Composition
from fhir.resources.documentreference import DocumentReferenceContent
from fhir.resources.fhirtypes import DateTime
from slugify import slugify
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
        return slugify(original_name)


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
    "ahd_payload_filename", ["payload_3.json", "payload_1_v5.json", "payload_2.json"]
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
    with open(f"tests/resources/ahd/{ahd_payload_filename}") as file:
        ahd_response = json.load(file)

    resource_handler = ResourceHandler(
        averbis_pipeline=MockPipeline(response=ahd_response),
        fixed_composition_datetime=doc.date,
    )

    result_bundle = resource_handler.handle_documents([doc])

    assert result_bundle.json(indent=2, ensure_ascii=False) == snapshot_fhir

@pytest.mark.parametrize('case_dir', list(Path('tests/test_cases').iterdir()))
def test_snapshot(case_dir, snapshot):

    ahd_json_path = "\\payload.json"

    doc = get_empty_document_reference(datetime(2023, 1, 1, tzinfo=timezone.utc))
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

    with open(f'{case_dir}{ahd_json_path}') as file:
        ahd_payload = json.load(file)

    resource_handler = ResourceHandler(
        averbis_pipeline=MockPipeline(response=ahd_payload)
    )
    
    bundle = resource_handler.handle_documents([doc])

    composition = bundle.entry[len(bundle.entry)-1]
    composition.resource.date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    composition.resource.title = 'test'

    result = bundle.json()

    snapshot.snapshot_dir = case_dir
    snapshot.assert_match(result, 'output_bundle.json')
    