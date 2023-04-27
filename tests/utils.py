import json
from datetime import datetime, timezone
from typing import Callable, Optional

from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.fhirtypes import DateTime
from fhir.resources.reference import Reference


def get_empty_document_reference(date: Optional[datetime] = None,) -> DocumentReference:
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
    if date is not None:
        docref.date = DateTime.validate(date)

    return docref


def map_resources(ahd_json_path: str, ahd_type: str, func: Callable, ahd_folder_path: str = 'tests/resources/ahd/') -> list:
    with open(f"{ahd_folder_path}{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    resources = []
    for val in ahd_payload:
        if val["type"] == ahd_type:
            resource = func(val, get_empty_document_reference(datetime(2023, 1, 1, tzinfo=timezone.utc)))
            if resource is not None:
                resources.append(resource)
    return resources
