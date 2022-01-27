import datetime
import json

from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.fhirtypes import DateTime
from fhir.resources.reference import Reference

from ahd2fhir.mappers.ahd_to_list import get_fhir_list


def get_example_payload(path):
    with open(path) as file:
        return json.load(file)


def get_empty_document_reference():
    doc_ref = DocumentReference.construct()
    doc_ref.status = "current"
    cnt = DocumentReferenceContent.construct()
    cnt.attachment = Attachment.construct()
    doc_ref.content = [cnt]
    subject_ref = Reference.construct()
    subject_ref.reference = "Patient/Test"
    subject_ref.type = "Patient"
    doc_ref.subject = subject_ref

    doc_ref.date = DateTime.validate(datetime.datetime.now(datetime.timezone.utc))

    return doc_ref


def test_fhir_discharge_list():
    annotations_without_discharge = get_example_payload(
        "tests/resources/ahd/payload_1.json"
    )
    annotations_with_discharge = get_example_payload(
        "tests/resources/ahd/payload_1.json"
    )

    discharge_list = get_fhir_list(
        annotations_without_discharge, get_empty_document_reference()
    )
    assert discharge_list is not None
    assert discharge_list.json()
    assert discharge_list.meta is not None
    assert discharge_list.emptyReason is not None

    discharge_list = get_fhir_list(
        annotations_with_discharge, get_empty_document_reference()
    )
    assert discharge_list is not None
    assert discharge_list.json()
    assert discharge_list.meta is not None
    assert discharge_list.emptyReason is None
