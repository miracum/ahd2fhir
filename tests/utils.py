from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.reference import Reference
from typing import Callable
import json


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
    docref.id = "empty-document"

    return docref


def map_resources(ahd_json_path: str, ahd_type: str, func: Callable) -> list:
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    resources = []
    for val in ahd_payload:
        if val["type"] == ahd_type:
            resource = func(val, get_empty_document_reference())
            if resource is not None:
                resources.append(resource)
    return resources
