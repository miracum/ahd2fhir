import datetime
import uuid
from typing import List

from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.fhirtypes import DateTime, QuantityType, ReferenceType
from fhir.resources.R4B.meta import Meta
from fhir.resources.R4B.observation import Observation
from structlog import get_logger

from ahd2fhir import config

log = get_logger()

FHIR_SYSTEMS = config.FhirSystemSettings()

CLINICAL_STATUS_MAPPING = {"ACTIVE": "active", "RESOLVED": "resolved"}
SIDE_MAPPING = {
    "LEFT": ("7771000", "Left"),
    "RIGHT": ("24028007", "Right"),
    "BOTH": ("51440002", "Right and left"),
}

UNIT_MAPPING = {"cm": "258672001", "mm": "258673006"}

OBSERVATION_PROFILE = (
    "https://www.medizininformatik-initiative.de/"
    + "fhir/core/StructureDefinition/Observation"
)
UKLFR_TYPE_KIDNEY_STONE = "de.uklfr.KidneyStoneAnnotator.KidneyStoneInfo"
AHD_TYPE = UKLFR_TYPE_KIDNEY_STONE

OBSERVATION_CATEGORY_SYSTEM = (
    "http://terminology.hl7.org/CodeSystem/observation-category"
)

STONE_DIMENSION_MAP = {
    "width": {
        "code": "9805-3",
        "name": "Width of Stone",
        "display": "Width (Stone) [Length]",
    },
    "length": {
        "code": "9799-8",
        "name": "Length of Stone",
        "display": "Length (Stone) [Length]",
    },
}


def get_fhir_resources(
    ahd_response_entry, document_reference: DocumentReference
) -> List[Observation]:
    return get_kidney_stone_from_annotation(
        annotation=ahd_response_entry,
        date=document_reference.date,
        doc_ref=document_reference,
    )


def fhirdate_now() -> DateTime:
    return DateTime.validate(datetime.datetime.now(datetime.timezone.utc))


def get_kidney_stone_from_annotation(
    annotation, date, doc_ref: DocumentReference
) -> List[Observation]:
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

    # Coding + Code
    observation_coding = Coding.construct()
    observation_coding.system = FHIR_SYSTEMS.snomed_ct
    observation_coding.code = "95570007"
    observation_coding.display = "Kidney stone (disorder)"
    observation_coding.userSelected = False
    observation_code = CodeableConcept.construct()
    observation_code.coding = [observation_coding]
    observation_code.text = "Kidney stone"
    observation.code = observation_code

    # Category
    observation_category = Coding.construct()
    observation_category.system = OBSERVATION_CATEGORY_SYSTEM
    observation_category.code = "imaging"
    observation_category.display = "Imaging"
    category = CodeableConcept.construct()
    category.coding = [observation_category]
    observation.category = [category]

    # Method
    observation_method = Coding.construct()
    observation_method.system = FHIR_SYSTEMS.snomed_ct
    observation_method.code = "363680008"
    observation_method.display = " Radiographic imaging procedure"
    method = CodeableConcept.construct()
    method.coding = [observation_method]
    observation.method = method

    # valueCodeableConcept
    value_codeable_concept = CodeableConcept()
    value_coding = Coding.construct()
    value_coding.system = FHIR_SYSTEMS.snomed_ct
    value_coding.code = "56381008"
    value_codeable_concept.coding = [value_coding]
    value_codeable_concept.text = "Calculus (morphologic abnormality)"
    observation.valueCodeableConcept = value_codeable_concept

    observations = [observation]

    # Create Observation for each Dimension (X/Y)
    if (stone_size := annotation["size"]) is not None:
        observation.hasMember = []
        stone_unit = stone_size["unit"]["coveredText"]
        stone_len = stone_size["value1"]
        stone_len_obs = stone_dimension_observation(
            observation, "length", stone_len, unit=stone_unit
        )
        observation.hasMember.append(stone_len_obs[1])
        observations.append(stone_len_obs[0])

        stone_width = stone_size["value2"]
        if stone_width in [0, "0"]:
            stone_width = stone_len
        stone_width_obs = stone_dimension_observation(
            observation, "width", stone_width, unit=stone_unit
        )
        observation.hasMember.append(stone_width_obs[1])
        observations.append(stone_width_obs[0])

    return observations


def stone_dimension_observation(
    parent: Observation, dimension: str, value: float, unit: str
):
    dimension_type = STONE_DIMENSION_MAP[dimension]
    # Observation details
    observation = Observation.construct()
    observation.status = "final"
    observation.meta = Meta.construct()
    observation.meta.profile = [OBSERVATION_PROFILE]
    observation.subject = parent.subject
    observation.effectiveDateTime = parent.effectiveDateTime
    observation.id = str(uuid.uuid4())

    # Coding
    observation_coding = Coding.construct()
    observation_coding.system = FHIR_SYSTEMS.loinc
    observation_coding.code = dimension_type["code"]
    observation_coding.display = dimension_type["display"]
    observation_coding.userSelected = False
    # Code
    observation_code = CodeableConcept.construct()
    observation_code.coding = [observation_coding]
    observation_code.text = dimension_type["name"]
    observation.code = observation_code

    # valueCodeableConcept
    value_quantity = QuantityType()
    value_quantity["system"] = FHIR_SYSTEMS.ucum
    value_quantity["code"] = unit
    value_quantity["value"] = value
    value_quantity["unit"] = unit
    observation.valueQuantity = value_quantity

    # Create Reference to Observation
    observation_reference = ReferenceType()
    observation_reference["reference"] = f"Observation/{observation.id}"
    observation_reference["display"] = observation.code.coding[0].display

    return observation, observation_reference
