import datetime
import re

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.documentreference import DocumentReference
from fhir.resources.fhirtypes import DateTime
from fhir.resources.identifier import Identifier
from fhir.resources.meta import Meta
from structlog import get_logger

from ahd2fhir import config
from ahd2fhir.utils.fhir_utils import sha256_of_identifier

log = get_logger()

FHIR_SYSTEMS = config.FhirSystemSettings()

CLINICAL_STATUS_MAPPING = {"ACTIVE": "active", "RESOLVED": "resolved"}
SIDE_MAPPING: dict[str, tuple[str, str]] = {
    "LEFT": ("7771000", "Left"),
    "RIGHT": ("24028007", "Right"),
    "BOTH": ("51440002", "Right and left"),
}

FHIR_SYSTEMS = config.FhirSystemSettings()

EXTRACT_YEAR_FROM_ICD_REGEX = r"ICD.*_(?P<version>\d{4})"


def get_fhir_condition(
    ahd_response_entry, document_reference: DocumentReference
) -> Condition:
    return get_condition_from_annotation(
        annotation=ahd_response_entry,
        doc_ref=document_reference,
    )


def get_condition_from_annotation(
    annotation, doc_ref: DocumentReference
) -> Condition | None:
    condition = Condition.construct()

    condition.subject = doc_ref.subject
    if doc_ref.date is not None:
        condition.recordedDate = doc_ref.date
    else:
        condition.recordedDate = DateTime.validate(
            datetime.datetime.now(datetime.timezone.utc)
        )

    condition.encounter = (
        doc_ref.context.encounter[0]
        if doc_ref.context is not None and len(doc_ref.context.encounter) > 0
        else None
    )

    condition_identifier = build_identifier_from_annotation(annotation, doc_ref)

    condition.identifier = [condition_identifier]

    condition.id = sha256_of_identifier(condition_identifier)

    condition.meta = Meta.construct()
    condition.meta.profile = [FHIR_SYSTEMS.condition_profile]

    if annotation.get("belongsTo") in ["FAMILY", "OTHER"]:
        log.warning("Dropped condition result because it refers to family history")
        return None

    if annotation.get("negatedBy") is not None:
        log.warning("Dropped condition result due to negation")
        return None

    # Terminologie
    if "ICD10GM" in str(annotation.get("source")):
        system = FHIR_SYSTEMS.icd_10_gm
    else:
        log.warning("Unknown coding source. Ignoring.", source=annotation.get("source"))
        return None

    condition_coding = Coding.construct()
    condition_coding.system = system
    condition_coding.display = annotation.get("dictCanon")
    condition_coding.code = annotation.get("conceptId")
    condition_coding.userSelected = False

    if match := re.search(EXTRACT_YEAR_FROM_ICD_REGEX, annotation.get("source")):
        condition_coding.version = match.group("version")
    else:
        log.warning(
            "Could not extract version from ICD system. Defaulting to '2020'",
            source=annotation.get("source"),
        )
        condition_coding.version = "2020"

    condition_code = CodeableConcept.construct()
    condition_code.coding = [condition_coding]

    condition.code = condition_code

    if clinical_status := annotation.get("clinicalStatus"):
        status_code = CLINICAL_STATUS_MAPPING.get(clinical_status)
        if status_code is not None:
            clinical_status_coding = Coding.construct()
            clinical_status_coding.system = FHIR_SYSTEMS.condition_clinical_status
            clinical_status_coding.code = status_code
            clinical_status_code = CodeableConcept.construct()
            clinical_status_code.coding = [clinical_status_coding]
            condition.clinicalStatus = clinical_status_code

    if (side := annotation.get("side")) is not None:
        body_side_snomed = SIDE_MAPPING.get(side)

        if body_side_snomed is None:
            log.warning(
                "Could not map body side from annotation to a SNOMED concept.",
                annotation_side=side,
            )
            return condition

        body_side_code = CodeableConcept.construct()
        body_side_code.coding = []

        body_side_coding = Coding.construct()
        body_side_coding.system = FHIR_SYSTEMS.snomed_ct
        body_side_coding.code = body_side_snomed[0]
        body_side_coding.display = body_side_snomed[1]

        body_side_code.coding.append(body_side_coding)

        condition.bodySite = []
        condition.bodySite.append(body_side_code)

    return condition


def build_identifier_from_annotation(annotation, doc_ref: DocumentReference):
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

    condition_identifier_system = (
        "https://fhir.miracum.org/nlp/identifiers/"
        + f"{annotation['type'].replace('.', '-').lower()}"
    )

    condition_identifier_value = (
        f"{doc_ref_identifier}_"
        + f"{annotation.get('begin')}-{annotation.get('end')}_"
        + f"{annotation.get('uniqueId')}".replace(":", "-")
    )

    return Identifier(
        **{"system": condition_identifier_system, "value": condition_identifier_value}
    )
