import json
import pytest
from pathlib import Path

from ahd2fhir.utils.device_builder import build_device
from ahd2fhir.utils.resource_handler import AHD_TYPE_DOCUMENT_ANNOTATION


def test_build_sets_version_identifier_and_id():
    with open("tests/resources/ahd/payload_1_v5.json") as file:
        ahd_payload = json.load(file)

    annotation = [
        a for a in ahd_payload if a["type"] == AHD_TYPE_DOCUMENT_ANNOTATION
    ].pop()

    device = build_device(annotation)

    assert device.json()

    assert len(device.version) == 1
    assert device.version[0].value == "5.29.0"

    assert len(device.identifier) == 1
    assert device.id is not None

@pytest.mark.parametrize('case_dir', list(Path('tests/test_cases').iterdir()))
def test_snapshot(case_dir, snapshot):

    ahd_json_path = "\\payload.json"

    with open(f'{case_dir}{ahd_json_path}') as file:
        ahd_payload = json.load(file)

    annotation = [
        a for a in ahd_payload if a["type"] == AHD_TYPE_DOCUMENT_ANNOTATION
    ].pop()

    device = build_device(annotation)
    result = device.json()

    snapshot.snapshot_dir = case_dir
    snapshot.assert_match(result, 'output_device_builder.json')
