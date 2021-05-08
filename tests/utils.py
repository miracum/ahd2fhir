from fhir.resources.attachment import Attachment
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.reference import Reference


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
