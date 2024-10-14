from hashlib import sha256

from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.fhirprimitiveextension import FHIRPrimitiveExtension
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.list import List
from fhir.resources.R4B.meta import Meta
from fhir.resources.R4B.reference import Reference
from structlog import get_logger

from ahd2fhir import config
from ahd2fhir.mappers.ahd_to_medication_statement import (
    get_medication_statement_from_annotation,
)
from ahd2fhir.utils.const import AHD_TYPE_MEDICATION

log = get_logger()

FHIR_SYSTEMS = config.FhirSystemSettings()

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

LIST_CONTEXT_CODE_MAPPING = {
    "ADMISSION": "E210",
    "INPATIENT": "E200",
    "DISCHARGE": "E230",
}
LIST_CONTEXT_CODE_SYSTEM = (
    "http://ihe-d.de/CodeSystems/FallkontextBeiDokumentenerstellung"
)

LIST_MED_CODE = "medications"
LIST_MED_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/list-example-use-codes"


def get_medication_statement_reference(annotation, document_reference):
    medication_statement = get_medication_statement_from_annotation(
        annotation, document_reference
    )

    if medication_statement is None:
        return None

    medication_reference = Reference.construct()
    medication_reference.type = f"{medication_statement.resource_type}"
    medication_reference.identifier = medication_statement.identifier[0]
    medication_reference.reference = (
        f"{medication_statement.resource_type}/{medication_statement.id}"
    )
    return medication_reference


# TODO: could be refactored to just return the list of List resources.
#       We simply append them to the final Bundle without any more logic anyways.
def get_fhir_list(annotation_results, document_reference: DocumentReference):
    """
    Returns a list of {statement: ..., medication: ...} tuples
    """
    return get_medication_list_from_document_reference(
        annotation_results=annotation_results, document_reference=document_reference
    )


def get_medication_list_from_document_reference(
    annotation_results, document_reference: DocumentReference
):
    base_list = List.construct(
        status="current",
        mode="snapshot",
        title="discharge",
        subject=document_reference.subject,
    )

    metadata = Meta.construct()
    metadata.profile = [FHIR_SYSTEMS.medication_list_profile]
    base_list.meta = metadata

    list_creation_date = document_reference.date
    base_list.date = list_creation_date

    document_identifier_value = (
        document_reference.identifier[0].value
        if document_reference.identifier is not None
        else document_reference.id
    )

    if len(annotation_results) < 1:
        return None

    med_entries: dict[str, list] = {"ADMISSION": [], "DISCHARGE": [], "INPATIENT": []}

    for annotation in annotation_results:
        if annotation["type"] != AHD_TYPE_MEDICATION:
            continue

        status = annotation.get("status")
        if status == "NEGATED" or status == "FAMILY":
            log.warning("annotation status is NEGATED or FAMILY.")
            continue
        if med_entries.keys().__contains__(status) is False:
            log.warning(
                "Annotation not part of admission, inpatient or discharge list."
            )
            continue

        medication_statement_reference = get_medication_statement_reference(
            annotation, document_reference
        )
        if medication_statement_reference is None:
            continue

        med_entry = {
            "item": medication_statement_reference,
        }

        # lst-3 "An entry date can only be used if the mode of the list is "working""
        if status == "INPATIENT":
            med_entry["date"] = document_reference.date

        med_entries[status].append(med_entry)

    result = {}

    # TODO: refactor to turn list_type into an enum for enhanced type safety
    for list_type in ["DISCHARGE", "ADMISSION", "INPATIENT"]:
        result[list_type] = base_list.copy(deep=True)
        result[list_type].entry = med_entries[list_type]
        result[list_type].title = f"List of {list_type.lower()} medication"

        # medication-list-context-2: Wenn der Kontext stationärer Aufenthalt ist,
        # soll der mode 'working' sein.
        if list_type == "INPATIENT":
            result[list_type].mode = "working"

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
            system=LIST_CONTEXT_CODE_SYSTEM, code=LIST_CONTEXT_CODE_MAPPING[list_type]
        )
        list_code = CodeableConcept.construct()
        list_code.text = "List Code"
        list_code.coding = [list_med_coding, list_coding]

        result[list_type].code = list_code

        list_identifier = Identifier.construct()
        list_identifier.system = (
            "https://fhir.miracum.org/nlp/identifiers/"
            + f"{list_type.lower()}-medication-list"
        )
        list_identifier.value = f"{list_type.lower()}_list_{document_identifier_value}"

        result[list_type].identifier = [list_identifier]
        result[list_type].id = sha256(
            f"{list_identifier.system}" f"|{list_identifier.value}".encode("utf-8")
        ).hexdigest()

    return result
