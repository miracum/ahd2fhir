import datetime
import json

from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.fhirtypes import DateTime
from fhir.resources.period import Period
from fhir.resources.reference import Reference

from ahd2fhir.config import Settings
from ahd2fhir.mappers.ahd_to_medication_statement import (
    get_fhir_medication_statement,
    get_medication_interval_from_annotation,
)
from ahd2fhir.utils.resource_handler import AHD_TYPE_MEDICATION


def get_example_payload():
    with open("tests/resources/ahd/payload_1.json") as file:
        return json.load(file)


def get_empty_document_reference():
    docref = DocumentReference.construct()
    docref.status = "current"
    cnt = DocumentReferenceContent.construct()
    cnt.attachment = Attachment.construct()
    docref.content = [cnt]
    subject_ref = Reference.construct()
    subject_ref.reference = "Patient/Test"
    subject_ref.type = "Patient"
    docref.subject = subject_ref

    docref.date = DateTime.validate(datetime.datetime.now(datetime.timezone.utc))

    return docref


def get_settings_override():
    return Settings(
        ahd_url="localhost",
        ahd_api_token="test",
        ahd_project="test",
        ahd_pipeline="test",
        ahd_version="5.0",
    )


def test_get_medication_interval_from_annotation_for_date():
    annotation = {"date": {"kind": "DATE", "value": "2018-01-01"}}
    date = get_medication_interval_from_annotation(annotation)
    assert date.isoformat() == DateTime.validate("2018-01-01").isoformat()


def test_get_medication_intverval_from_annotation_for_date_interval():
    annotation = {
        "date": {
            "kind": "DATEINTERVAL",
            "startDate": "2018-01-01",
            "endDate": "2019-01-01",
        }
    }
    assert isinstance(get_medication_interval_from_annotation(annotation), Period)


def test_fhir_medication():
    annotation = [a for a in get_example_payload() if a["type"] == AHD_TYPE_MEDICATION][
        0
    ]

    result = get_fhir_medication_statement(
        annotation,
        settings=get_settings_override(),
        document_reference=get_empty_document_reference(),
    )

    medication = result[0]["medication"]
    assert medication.json()
    assert medication.ingredient is not None
    assert medication.meta is not None

    statement = result[0]["statement"]
    assert statement.json()
    assert statement.status is not None
    assert statement.medicationReference is not None
