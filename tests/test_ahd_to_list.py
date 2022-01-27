import datetime
import json

from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.fhirtypes import DateTime
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from ahd2fhir.mappers.ahd_to_list import get_fhir_list
from ahd2fhir.utils.resource_handler import AHD_TYPE_MEDICATION


def get_example_payload(path):
    with open(path) as file:
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


def test_fhir_discharge_list():
    # "tests/resources/ahd/payload_1.json"
    annotations_without_discharge = get_example_payload("resources/ahd/payload_1.json")
    annotations_with_discharge = get_example_payload("resources/ahd/payload_3.json")

    discharge_list = get_fhir_list(annotations_without_discharge,
                                   get_empty_document_reference())
    assert discharge_list is not None
    assert discharge_list.json()
    assert discharge_list.meta is not None
    assert discharge_list.emptyReason is not None

    discharge_list = get_fhir_list(annotations_with_discharge,
                                   get_empty_document_reference())
    assert discharge_list is not None
    assert discharge_list.json()
    assert discharge_list.meta is not None
    assert discharge_list.emptyReason is None
