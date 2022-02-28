import json

from ahd2fhir.mappers.ahd_to_device import AHD_TYPE_DOCUMENT_ANNOTATION, build_device


def test_build_sets_version_identifier_and_id():
    with open("tests/resources/ahd/payload_1.json") as file:
        ahd_payload = json.load(file)

    annotation = [
        a for a in ahd_payload if a["type"] == AHD_TYPE_DOCUMENT_ANNOTATION
    ].pop()

    device = build_device(annotation, None)

    assert device.json()

    assert len(device.version) == 1
    assert device.version[0].value == "5.29.0"

    assert len(device.identifier) == 1
    assert device.id is not None
