import re
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.medication import Medication, MedicationIngredient
from fhir.resources.R4B.meta import Meta
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.ratio import Ratio
from fhir.resources.R4B.fhirprimitiveextension import FHIRPrimitiveExtension
from structlog import get_logger
from slugify import slugify

from ahd2fhir import config
from ahd2fhir.utils.fhir_utils import sha256_of_identifier

log = get_logger()

FHIR_SYSTEMS = config.FhirSystemSettings()

DATA_ABSENT_EXTENSION_UNSUPPORTED = FHIRPrimitiveExtension(
    **{
        "extension": [
            {
                "url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason",
                "valueCode": "unsupported",
            }
        ]
    }
)

# TODO: this needs refactoring to make sure it's actually compatible with the MII Medication Profiles
#       disabled as of now.
def get_medication_from_annotation(annotation: dict) -> Medication | None:
    medication = Medication.construct()

    # Medication Meta
    medication.meta = Meta.construct()
    medication.meta.profile = [FHIR_SYSTEMS.medication_profile]
    
    annotation_type_lowercase = annotation['type'].replace('.', '-').lower()
    medication_identifier_system = f"{FHIR_SYSTEMS.ahd_to_fhir_base_url}/identifiers/{annotation_type_lowercase}"

    # Medication Code
    atc_codes = annotation.get("atcCodes", [])

    if len(atc_codes) == 0:
        log.warn("No ATC code set for medication. Not mapping")
        return None
    
    drugs = annotation["drugs"]

    if len(drugs) > 1:
        log.warning(
            "More than one drugs entry found. Defaulting to only the first entry."
        )
        
    drug = drugs[0]
    
    identifier = Identifier()
    identifier.system = medication_identifier_system
    identifier.value = slugify(drug["ingredient"]["uniqueID"])
    medication.identifier = [identifier]

    medication.id = sha256_of_identifier(identifier)
    
    medication_code = CodeableConcept.construct()
    medication_code.coding = []

    for atc_code in atc_codes:
        coding = Coding.construct()
        coding.system = FHIR_SYSTEMS.atc
        coding.code = atc_code["conceptID"]
        coding.display = atc_code["dictCanon"]

        year_match = re.search(r"_(\d{4})$", atc_code["source"])
        if year_match:
            year = year_match.group(1)
            coding.version = year
        else:
            log.warn(f"Unable to extract version from atcCode source: {atc_code["source"]}")

        medication_code.coding.append(coding)

    medication.code = medication_code

    # Medication Ingredient
    ingredient = MedicationIngredient.construct()

    # the AHD annotation does not contain ingredient info in one of the required
    # codings - ASK, SNOMED, CAS, UNII (https://simplifier.net/guide/mii-ig-modul-medikation-2024-de/MIIIGModulMedikation/TechnischeImplementierung/FHIR-Profile/Medication?version=current)
    ingredient.extension = [DATA_ABSENT_EXTENSION_UNSUPPORTED]
    medication.ingredient = [ingredient]

    ingredient.itemCodeableConcept = CodeableConcept.construct()
    ingredient.itemCodeableConcept.coding = [Coding()]
    ingredient.itemCodeableConcept.coding[0].display = drug_display
    ingredient.itemCodeableConcept.coding[0].system = system

    if (
        "strength" not in drug
        or drug["strength"] is None
        or "value" not in drug["strength"]
        or "unit" not in drug["strength"]
        or drug["strength"]["value"] is None
        or drug["strength"]["unit"] is None
    ):
        return medication

    strength = Ratio.construct()

    numerator = Quantity.construct()
    numerator.value = drug["strength"]["value"]
    numerator.unit = drug["strength"]["unit"]
    strength.numerator = numerator

    identifier.value = (
        drug["ingredient"]["dictCanon"]
        + "_"
        + str(drug["strength"]["value"])
        + drug["strength"]["unit"]
    )
    medication.id = sha256_of_identifier(identifier)

    if "doseForm" not in annotation or annotation["doseForm"] is None:
        return medication

    denominator = Quantity.construct()
    denominator.value = 1
    denominator.unit = annotation["doseForm"]["dictCanon"]
    strength.denominator = denominator

    ingredient.strength = strength

    identifier.value = (
        drug["ingredient"]["dictCanon"]
        + "_"
        + str(drug["strength"]["value"])
        + drug["strength"]["unit"]
        + "_"
        + annotation["doseForm"]["dictCanon"]
    )

    medication.id = sha256_of_identifier(identifier)

    return medication
