import datetime
import json

from fhir.resources.R4B.attachment import Attachment
from fhir.resources.R4B.documentreference import (
    DocumentReference,
    DocumentReferenceContent,
)
from fhir.resources.R4B.fhirtypes import DateTime
from fhir.resources.R4B.period import Period
from fhir.resources.R4B.reference import Reference

from ahd2fhir.mappers.ahd_to_medication_statement import (
    get_fhir_medication_statement,
    get_medication_interval_from_annotation,
)
from ahd2fhir.utils.resource_handler import AHD_TYPE_MEDICATION


def get_example_payload_v6():
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


def test_get_medication_interval_from_annotation_for_date():
    annotation = {"date": {"kind": "DATE", "value": "2018-01-01"}}
    date = get_medication_interval_from_annotation(annotation)
    assert date is not None
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


def test_fhir_medication_v6():
    annotation_v6 = [
        a for a in get_example_payload_v6() if a["type"] == AHD_TYPE_MEDICATION
    ][0]

    statement_v6 = get_fhir_medication_statement(
        annotation_v6, get_empty_document_reference()
    )

    assert statement_v6.json()
    assert statement_v6.status is not None
    assert statement_v6.medicationReference is None
    assert statement_v6.medicationCodeableConcept is not None
