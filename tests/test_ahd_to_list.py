import datetime
import json
import os
from unittest import mock

from fhir.resources.R4B.attachment import Attachment
from fhir.resources.R4B.documentreference import (
    DocumentReference,
    DocumentReferenceContent,
)
from fhir.resources.R4B.fhirtypes import DateTime
from fhir.resources.R4B.reference import Reference

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
    annotations_with_discharge = get_example_payload(
        "tests/resources/ahd/payload_3.json"
    )

    lists_with_discharge = get_fhir_list(
        annotations_with_discharge, get_empty_document_reference()
    )

    assert lists_with_discharge is not None

    discharge_list = lists_with_discharge["DISCHARGE"]

    assert discharge_list is not None
    assert discharge_list.json()
    assert discharge_list.meta is not None
    assert discharge_list.emptyReason is None
