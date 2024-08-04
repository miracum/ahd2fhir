import json

from ahd2fhir.utils.device_builder import build_device
from ahd2fhir.utils.resource_handler import AHD_TYPE_DOCUMENT_ANNOTATION


def test_build_sets_version_identifier_and_id():
    with open("tests/resources/ahd/payload_1.json") as file:
        ahd_payload = json.load(file)

    annotation = [
        a for a in ahd_payload if a["type"] == AHD_TYPE_DOCUMENT_ANNOTATION
    ].pop()

    device = build_device(annotation)

    assert device.json()

    assert len(device.version) == 1
    assert device.version[0].value == "7.4.0"

    assert len(device.identifier) == 1
    assert device.id is not None
