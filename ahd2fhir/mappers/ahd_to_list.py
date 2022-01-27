from hashlib import sha256

from fhir.resources.documentreference import DocumentReference
from fhir.resources.fhirprimitiveextension import FHIRPrimitiveExtension
from fhir.resources.fhirtypes import DateTime
from fhir.resources.identifier import Identifier
from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference
from fhir.resources.list import List
from fhir.resources.meta import Meta
from structlog import get_logger

from ahd2fhir.mappers.ahd_to_medication_statement import \
    get_medication_statement_from_annotation
from ahd2fhir.utils.resource_handler import AHD_TYPE_MEDICATION

log = get_logger()

LIST_PROFILE = (
    "https://www.medizininformatik-initiative.de/"
    + "fhir/core/modul-medikation/StructureDefinition/List"
)

DATA_ABSENT_EXTENSION_UNKNOWN = FHIRPrimitiveExtension(
    **{
        "extension": [
            {
                "url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason",
                "valueCode": "unknown",
            }
        ]
    }
)


def get_fhir_list(annotation_results, document_reference: DocumentReference):
    """
    Returns a list of {statement: ..., medication: ...} tuples
    """
    return get_medication_list_from_document_reference(
        annotation_results=annotation_results,
        document_reference=document_reference
    )


def get_medication_list_from_document_reference(
    annotation_results,
    document_reference: DocumentReference
):

    discharge_list = List.construct(
        status="current",
        mode="snapshot",
        title="discharge",
        subject=document_reference.subject
    )

    metadata = Meta.construct()
    metadata.profile = [LIST_PROFILE]
    discharge_list.meta = metadata

    list_creation_date = DateTime.now()
    discharge_list.date = list_creation_date

    document_identifier_value = (
        document_reference.identifier[0].value
        if document_reference.identifier is not None
        else None
    )
    list_identifier = Identifier.construct()
    list_identifier.system = (
            "https://fhir.miracum.org/nlp/identifiers/discharge_list"
    )
    list_identifier.value = f"discharge_list_{document_identifier_value}"

    discharge_list.id = sha256(
        f"{list_identifier.system}"
        f"|{list_identifier.value}".encode("utf-8")
    ).hexdigest()

    if len(annotation_results) < 1:
        return None

    discharge_entries = []
    num_entries = 0
    for annotation in annotation_results:
        if annotation["type"] != AHD_TYPE_MEDICATION:
            continue

        if annotation["status"] == "NEGATED" or annotation["status"] == "FAMILY":
            log.warning("annotation status is NEGATED or FAMILY. Ignoring.")
            continue
        if annotation["status"] != "DISCHARGE":
            log.warning("Annotation not part of discharge list. Ignoring.")
            continue
        num_entries += 1
        discharge_entry = {}
        medication_statement = get_medication_statement_from_annotation(
            annotation, document_reference
        )[0]['statement']
        medication_reference = Reference.construct()
        medication_reference.type = f"{medication_statement.resource_type}"
        medication_reference.identifier = medication_statement.identifier[0]
        medication_reference.reference = \
            f"{medication_statement.resource_type}/{medication_statement.id}"

        discharge_entry["date"] = DateTime.now()
        discharge_entry["item"] = medication_reference
        discharge_entries.append(discharge_entry)

    discharge_list.entry = discharge_entries

    if num_entries == 0:
        empty_reason_coding = Coding.construct(
            display="No discharge entries in document found."
        )
        empty_reason = CodeableConcept.construct(
            text="No discharge entries in document found.",
            code=empty_reason_coding
        )
        discharge_list.emptyReason = empty_reason

    return discharge_list
