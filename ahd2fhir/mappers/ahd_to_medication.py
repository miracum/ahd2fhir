from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.identifier import Identifier
from fhir.resources.medication import Medication, MedicationIngredient
from fhir.resources.meta import Meta
from fhir.resources.quantity import Quantity
from fhir.resources.ratio import Ratio
from structlog import get_logger

from ahd2fhir.config import Settings
from ahd2fhir.utils.fhir_utils import sha256_of_identifier

log = get_logger()

MEDICATION_PROFILE = (
    "https://www.medizininformatik-initiative.de/"
    + "fhir/core/modul-medikation/StructureDefinition/Medication"
)


def get_medication_from_annotation(annotation) -> Medication | None:
    medication = Medication.construct()

    drug = annotation["drugs"][0]
    if drug.get("ingredient") is None:
        return None

    # Medication Meta
    medication.meta = Meta.construct()
    medication.meta.profile = [MEDICATION_PROFILE]

    # Medication Code
    codes = []
    if Settings().ahd_version.split(".")[0] == "5":
        if "Abdamed-Averbis" in str(drug["ingredient"]["source"]):
            system = "http://fhir.de/CodeSystem/dimdi/atc"
            codes = str(drug["ingredient"]["conceptId"]).split("-")
        elif "RxNorm" in str(drug["ingredient"]["source"]):
            system = "http://www.nlm.nih.gov/research/umls/rxnorm"
            codes.append(str(drug["ingredient"]["conceptId"]))
        else:
            system = ""
    elif Settings().ahd_version.split(".")[0] == "6":  # ahd v.6
        system = "http://fhir.de/CodeSystem/dimdi/atc"
        codes.append(annotation["atc"])
    else:
        system = ""

    med_code = CodeableConcept.construct()
    med_code.coding = []
    for code in codes:
        med_coding = Coding.construct()
        med_coding.system = system
        med_coding.display = drug["ingredient"]["dictCanon"]
        med_coding.code = code
        med_code.coding.append(med_coding)

    medication.code = med_code

    # Medication Ingredient
    ingredient = MedicationIngredient.construct()
    medication.ingredient = [ingredient]

    ingredient.itemCodeableConcept = CodeableConcept.construct()
    ingredient.itemCodeableConcept.coding = [Coding()]
    ingredient.itemCodeableConcept.coding[0].display = drug["ingredient"]["dictCanon"]
    ingredient.itemCodeableConcept.coding[0].system = system

    medication_identifier_system = (
        "https://fhir.miracum.org/nlp/identifiers/"
        + f"{annotation['type'].replace('.', '-').lower()}"
    )
    medication.identifier = [Identifier()]
    medication.identifier[0].value = drug["ingredient"]["dictCanon"]
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
