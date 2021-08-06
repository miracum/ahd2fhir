import hashlib

import structlog
from fhir.resources.device import Device, DeviceDeviceName, DeviceVersion
from fhir.resources.identifier import Identifier

# from ahd2fhir.utils.custom_mappers import Mapper

log = structlog.get_logger()

AHD_DEVICE_IDENTIFIER_SYSTEM = (
    "https://fhir.miracum.org/nlp/identifiers/averbis-health-discovery-device-id"
)

AHD_TYPE_DOCUMENT_ANNOTATION = "de.averbis.types.health.DocumentAnnotation"


def build_device(document_annotation) -> Device:
    ahd_version = document_annotation.get("version")

    identifier = Identifier(
        **{
            "system": AHD_DEVICE_IDENTIFIER_SYSTEM,
            "value": f"ahd-v{ahd_version}",
        }
    )

    device = Device.construct()
    device.status = "active"
    device.manufacturer = "Averbis GmbH"
    device.deviceName = [
        DeviceDeviceName(
            **{"name": "Averbis Health Discovery", "type": "manufacturer-name"}
        )
    ]
    device.version = [DeviceVersion(**{"value": ahd_version})]
    device.identifier = [identifier]

    device_id_plain = f"{identifier.system}|{identifier.value}"
    device.id = hashlib.sha256(device_id_plain.encode("utf-8")).hexdigest()

    return device
