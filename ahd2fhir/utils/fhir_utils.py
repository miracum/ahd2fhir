import base64
import datetime
import time
from hashlib import sha256
from typing import List, Tuple

import structlog
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.composition import Composition, CompositionSection
from fhir.resources.documentreference import DocumentReference
from fhir.resources.fhirtypes import DateTime
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.resource import Resource

log = structlog.get_logger()


DISCHARGE_SUMMARY_CONCEPT_TEXT = (
    "Clinical document Kind of document from LOINC Document Ontology"
)

DISCHARGE_SUMMARY_CONCEPT = CodeableConcept(
    **{
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "74477-1",
                "display": DISCHARGE_SUMMARY_CONCEPT_TEXT,
            },
        ],
        "text": DISCHARGE_SUMMARY_CONCEPT_TEXT,
    }
)


def sha256_of_identifier(identifier: Identifier) -> str:
    return sha256(f"{identifier.system}|{identifier.value}".encode("utf-8")).hexdigest()


def _extract_text_from_resource(
    document_reference: DocumentReference,
) -> Tuple[str, str]:
    valid_content = [
        content
        for content in document_reference.content
        if content.attachment.data is not None
    ]

    if len(valid_content) == 0:
        raise ValueError(f"Document {document_reference.id} contains no valid content")

    if len(valid_content) > 1:
        raise ValueError(
            f"Document {document_reference.id} contains more than one attachment"
        )

    content = valid_content[0]

    language = None
    if content.attachment.language:
        language = content.attachment.language.lower().split("-")[0]

    return (
        base64.b64decode(content.attachment.data).decode("utf8"),
        content.attachment.contentType,
        language,
    )


def _build_composition_identifier_from_documentreference(
    doc_ref: DocumentReference,
):
    """
    construct a hopefully unqiue identifier for the condition from
    the document identifier as well as the offset into the text
    and the unique id of the annotation
    """
    doc_ref_identifier = None
    if doc_ref.identifier is None or len(doc_ref.identifier) == 0:
        log.warning(
            "No identifier specified on the document. "
            + "Trying to fall-back to the DocumentReference.id"
        )
        doc_ref_identifier = doc_ref.id
    else:
        if len(doc_ref.identifier) > 1:
            log.warning(
                "More than one identifier specified on the document. "
                + "Using the first occurrence."
            )
        doc_ref_identifier = doc_ref.identifier[0].value

    composition_identifier_system = (
        "https://fhir.miracum.org/nlp/identifiers/ahd-analysis-result-composition"
    )

    composition_identifier_value = f"{doc_ref_identifier}_ahd-analysis-result"

    return Identifier(
        **{
            "system": composition_identifier_system,
            "value": composition_identifier_value,
        }
    )


def _build_composition(
    document_reference: DocumentReference, all_resources: List[Resource]
):
    composition_type = (
        document_reference.type
        if document_reference.type is not None
        else DISCHARGE_SUMMARY_CONCEPT
    )

    composition_subject = document_reference.subject
    composition_category = document_reference.category
    composition_encounter = None

    if document_reference.context is not None:
        if len(document_reference.context.encounter) > 1:
            log.warning(
                "DocumentReference contains more than one encounter. "
                + "Using the first."
            )
        composition_encounter = document_reference.context.encounter[0]

    composition_author = None
    composition_sections = []
    for resource in all_resources:
        resource_type = resource.resource_type

        if resource_type == "Device":
            author = Reference.construct()
            author.reference = f"Device/{resource.id}"
            author.type = "Device"
            composition_author = author
            continue

        # Check if no resource specific section exists ands adds it,
        # otherwise select the correct section
        if not any(section.title == resource_type for section in composition_sections):
            resource_section = CompositionSection.construct()
            resource_section.title = resource_type
            resource_section.entry = []

            composition_sections.append(resource_section)

            ind = len(composition_sections) - 1
        else:
            ind = [
                ind
                for ind, section in enumerate(composition_sections)
                if section.title == resource_type
            ][0]

        entry_reference = Reference.construct()
        entry_reference.reference = resource_type + "/" + resource.id

        composition_sections[ind].entry.append(entry_reference)

    if composition_author is None:
        composition_author = Reference(**{"display": "Averbis Health Discovery"})

    composition_identifier = _build_composition_identifier_from_documentreference(
        document_reference
    )

    composition = Composition(
        **{
            "title": "NLP FHIR Results " + time.strftime("%Y-%m-%dT%H:%M"),
            "status": "final",
            "date": DateTime.validate(datetime.datetime.now(datetime.timezone.utc)),
            "type": composition_type,
            "identifier": composition_identifier,
            "id": sha256_of_identifier(composition_identifier),
            "subject": composition_subject,
            "category": composition_category,
            "encounter": composition_encounter,
            "author": [composition_author],
            "section": composition_sections,
        }
    )
    return composition
