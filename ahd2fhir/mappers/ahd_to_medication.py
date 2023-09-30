from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.identifier import Identifier
from fhir.resources.medication import Medication, MedicationIngredient
from fhir.resources.meta import Meta
from fhir.resources.quantity import Quantity
from fhir.resources.ratio import Ratio
from structlog import get_logger

from ahd2fhir import config
from ahd2fhir.utils.fhir_utils import sha256_of_identifier

log = get_logger()

MEDICATION_PROFILE = (
    "https://www.medizininformatik-initiative.de/"
    + "fhir/core/modul-medikation/StructureDefinition/Medication"
)

FHIR_SYSTEMS = config.FhirSystemSettings()


def get_medication_from_annotation(annotation) -> Medication | None:
    medication = Medication.construct()

    drugs = annotation["drugs"]

    if len(drugs) > 1:
        log.warning(
            "More than one drugs entry found. Defaulting to only the first entry."
        )

    drug = drugs[0]
    if drug.get("ingredient") is None:
        log.error("No ingredient set for the drug annotation")
        return None

    # Medication Meta
    medication.meta = Meta.construct()
    medication.meta.profile = [MEDICATION_PROFILE]

    # Medication Code
    codes = []
    if "abdamed" in str(drug["ingredient"]["source"]).lower():
        system = FHIR_SYSTEMS.atc
        codes = str(drug["ingredient"]["conceptID"]).split("-")
    elif "rxnorm" in str(drug["ingredient"]["source"]).lower():
        system = FHIR_SYSTEMS.rxnorm
        codes.append(str(drug["ingredient"]["conceptID"]))
    else:
        system = ""

    drug_display = drug["ingredient"]["dictCanon"]

    med_code = CodeableConcept.construct()
    med_code.coding = []
    for code in codes:
        med_coding = Coding.construct()
        med_coding.system = system
        med_coding.display = drug_display
        med_coding.code = code
        med_code.coding.append(med_coding)

    medication.code = med_code

    # Medication Ingredient
    ingredient = MedicationIngredient.construct()
    medication.ingredient = [ingredient]

    ingredient.itemCodeableConcept = CodeableConcept.construct()
    ingredient.itemCodeableConcept.coding = [Coding()]
    ingredient.itemCodeableConcept.coding[0].display = drug_display
    ingredient.itemCodeableConcept.coding[0].system = system

    medication_identifier_system = (
        "https://fhir.miracum.org/nlp/identifiers/"
        + f"{annotation['type'].replace('.', '-').lower()}"
    )
    medication.identifier = [Identifier()]
    medication.identifier[0].value = drug_display
    medication.identifier[0].system = medication_identifier_system

    medication.id = sha256_of_identifier(medication.identifier[0])

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

    medication.identifier[0].value = (
        drug["ingredient"]["dictCanon"]
        + "_"
        + str(drug["strength"]["value"])
        + drug["strength"]["unit"]
    )
    medication.id = sha256_of_identifier(medication.identifier[0])

    if "doseForm" not in annotation or annotation["doseForm"] is None:
        return medication

    denominator = Quantity.construct()
    denominator.value = 1
    denominator.unit = annotation["doseForm"]["dictCanon"]
    strength.denominator = denominator

    ingredient.strength = strength

    medication.identifier[0].value = (
        drug["ingredient"]["dictCanon"]
        + "_"
        + str(drug["strength"]["value"])
        + drug["strength"]["unit"]
        + "_"
        + annotation["doseForm"]["dictCanon"]
    )

    medication.id = sha256_of_identifier(medication.identifier[0])

    return medication
