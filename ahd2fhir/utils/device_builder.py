import hashlib

import structlog
from fhir.resources.R4B.device import Device, DeviceDeviceName, DeviceVersion
from fhir.resources.R4B.identifier import Identifier

log = structlog.get_logger()

AHD_DEVICE_IDENTIFIER_SYSTEM = (
    "https://fhir.miracum.org/nlp/identifiers/averbis-health-discovery-device-id"
)


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
