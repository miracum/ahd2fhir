import datetime
import os
import uuid
from typing import List

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.documentreference import DocumentReference
from fhir.resources.fhirtypes import DateTime, String
from fhir.resources.meta import Meta
from fhir.resources.observation import Observation
from structlog import get_logger

log = get_logger()

OBSERVATION_PROFILE = (
    "https://www.medizininformatik-initiative.de/"
    + "fhir/core/StructureDefinition/Observation"
)
UKLFR_TYPE_SMKSTAT = "de.medunifreiburg.imbi.mds.extraction.types.Smoking"
AHD_TYPE = UKLFR_TYPE_SMKSTAT

OBSERVATION_CATEGORY_SYSTEM = (
    "http://terminology.hl7.org/CodeSystem/observation-category"
)

SNOMED_LOINC_MAPPING = {
    "PAST-SMOKER": {"code": "LA15920-4", "text": "Former smoker"},
    "CURRENT-SMOKER": {"code": "LA18976-3", "text": "Current every day smoker"},
    "CURRENT-NON-SMOKER": {"code": "LA15920-4", "text": "Former smoker"},
    "NEVER-SMOKER": {"code": "LA18978-9", "text": "Never smoker"},
    "CURRENT-OR-PAST-SMOKER": {
        "code": "LA18979-7",
        "text": "Smoker, current status unknown",
    },
    "UNKNOW": {"code": "LA18980-5", "text": "Unknown if ever smoked"},
}


def get_fhir_smoking_status(
    ahd_response_entry, document_reference: DocumentReference
) -> List[Observation]:
    return get_smoking_status_observation_from_annotation(
        annotation=ahd_response_entry,
        date=document_reference.date,
        doc_ref=document_reference,
    )


def fhirdate_now():
    return DateTime.validate(datetime.datetime.now(datetime.timezone.utc))


def get_smoking_status_observation_from_annotation(
    annotation, date, doc_ref: DocumentReference
):
    # Observation details
    observation = Observation.construct()
    observation.status = "final"
    observation.meta = Meta.construct()
    observation.meta.profile = [OBSERVATION_PROFILE]
    observation.subject = doc_ref.subject
    observation.effectiveDateTime = date or fhirdate_now()
    observation.id = str(uuid.uuid4())
    observation.encounter = (
        doc_ref.context.encounter[0] if doc_ref.context is not None else None
    )

    # Coding
    observation_coding = Coding.construct()
    observation_coding.system = "http://loinc.org"
    observation_coding.code = "72166-2"
    observation_coding.display = "Tobacco smoking status"
    observation_coding.userSelected = False

    # Code
    observation_code = CodeableConcept.construct()
    observation_code.coding = [observation_coding]
    observation_code.text = "Tobacco smoking status"
    observation.code = observation_code

    # Category
    observation_category = Coding.construct()
    observation_category.system = OBSERVATION_CATEGORY_SYSTEM
    observation_category.code = "social-history"
    observation_category.display = "Social History"
    category = CodeableConcept.construct()
    category.coding = [observation_category]
    observation.category = [category]

    smkstat = SNOMED_LOINC_MAPPING[annotation["smokingStatus"]]

    # If SMKSTAT_AS_VALUESTRING is set
    if os.getenv("SMKSTAT_AS_VALUESTRING", "").lower() in ["true", 1, "yes"]:
        # Code Resource as fhirTypes.valueString
        observation.valueString = String(smkstat["text"])
    else:
        # Code Resource as valueCodeableConcept
        codeable_concept = CodeableConcept()

        # Create LOINC coding
        coding_loinc = Coding.construct()
        coding_loinc.system = "http://loinc.org"
        coding_loinc.code = smkstat["code"]

        # Create snomed coding
        coding_snomed = Coding.construct()
        coding_snomed.system = "http://snomed.info/sct"
        coding_snomed.code = annotation["sctid"]

        codeable_concept.coding = [coding_loinc, coding_snomed]
        codeable_concept.text = smkstat["text"]
        observation.valueCodeableConcept = codeable_concept

    # if pack_years := annotation["packYears"] != "null":
    # valueCodeableConcept
    # value_quantity = QuantityType()
    # value_quantity["value"] = pack_years
    # value_quantity.system = "http://snomed.info/sct"
    # value_quantity.code = "401201003"
    # value_quantity.text = "401201003"
    # observation.valueQuantity = value_quantity
    return [observation]
