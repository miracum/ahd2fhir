from hashlib import sha256

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.documentreference import DocumentReference
from fhir.resources.fhirprimitiveextension import FHIRPrimitiveExtension
from fhir.resources.identifier import Identifier
from fhir.resources.list import List
from fhir.resources.meta import Meta
from fhir.resources.reference import Reference
from structlog import get_logger

from ahd2fhir.config import Settings
from ahd2fhir.mappers.ahd_to_medication_statement import (
    get_medication_statement_from_annotation,
)

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

LIST_CODE_MAPPING = {"ADMISSION": "E210", "INPATIENT": "E200", "DISCHARGE": "E230"}
LIST_CODE_SYSTEM = "urn:oid:1.3.6.1.4.1.19376.3.276.1.5.16"

LIST_MED_CODE = "medications"
LIST_MED_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/list-example-use-codes"


def get_medication_statement_reference(annotation, settings, document_reference):
    medication_statement = get_medication_statement_from_annotation(
        annotation, settings, document_reference
    )[0]["statement"]
    medication_reference = Reference.construct()
    medication_reference.type = f"{medication_statement.resource_type}"
    medication_reference.identifier = medication_statement.identifier[0]
    medication_reference.reference = (
        f"{medication_statement.resource_type}/{medication_statement.id}"
    )
    return medication_reference


def get_fhir_list(annotation_results, settings, document_reference: DocumentReference):
    """
    Returns a list of {statement: ..., medication: ...} tuples
    """
    return get_medication_list_from_document_reference(
        annotation_results=annotation_results,
        settings=settings,
        document_reference=document_reference,
    )


def get_medication_list_from_document_reference(
    annotation_results, settings, document_reference: DocumentReference
):

    base_list = List.construct(
        status="current",
        mode="snapshot",
        title="discharge",
        subject=document_reference.subject,
    )

    metadata = Meta.construct()
    metadata.profile = [LIST_PROFILE]
    base_list.meta = metadata

    list_creation_date = document_reference.date
    base_list.date = list_creation_date

    document_identifier_value = (
        document_reference.identifier[0].value
        if document_reference.identifier is not None
        else None
    )

    if len(annotation_results) < 1:
        return None

    med_entries = {"ADMISSION": [], "DISCHARGE": [], "INPATIENT": []}

    num_entries = 0
    for annotation in annotation_results:
        if annotation["type"] != "de.averbis.types.health.Medication":
            continue
        if annotation["status"] == "NEGATED" or annotation["status"] == "FAMILY":
            log.warning("annotation status is NEGATED or FAMILY.")
            continue
        if med_entries.keys().__contains__(annotation["status"]) is False:
            log.warning(
                "Annotation not part of admission, inpatient or discharge list."
            )
            continue
        num_entries += 1
        med_entry = {
            "date": document_reference.date,
            "item": get_medication_statement_reference(
                annotation=annotation,
                settings=Settings,
                document_reference=document_reference,
            ),
        }
        med_entries[annotation["status"]].append(med_entry)

    result = {}

    for list_type in ["DISCHARGE", "ADMISSION", "INPATIENT"]:
        result[list_type] = base_list.copy(deep=True)
        result[list_type].entry = med_entries[list_type]
        result[list_type].title = list_type.lower()
        empty_reason_coding = Coding.construct(
            display="No {} entries in document found.".format(list_type.lower())
        )
        empty_reason = CodeableConcept.construct(
            text="No {} entries in document found.".format(list_type.lower()),
            code=empty_reason_coding,
        )
        if len(med_entries[list_type]) == 0:
            result[list_type].emptyReason = empty_reason

        list_med_coding = Coding.construct(
            system=LIST_MED_CODE_SYSTEM, code=LIST_MED_CODE
        )
        list_coding = Coding.construct(
            system=LIST_CODE_SYSTEM, code=LIST_CODE_MAPPING[list_type]
        )
        list_code = CodeableConcept.construct(text="List Code", code=[])
        list_code.code.append(list_med_coding)
        list_code.code.append(list_coding)
        result[list_type].code = list_code

        list_identifier = Identifier.construct()
        list_identifier.system = (
            "https://fhir.miracum.org/nlp/identifiers/discharge_list"
        )
        list_identifier.value = f"{list_type.lower()}_list_{document_identifier_value}"
        result[list_type].id = sha256(
            f"{list_identifier.system}" f"|{list_identifier.value}".encode("utf-8")
        ).hexdigest()

    return result
