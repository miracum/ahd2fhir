import re
from typing import Union

from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.dosage import Dosage, DosageDoseAndRate
from fhir.resources.R4B.fhirprimitiveextension import FHIRPrimitiveExtension
from fhir.resources.R4B.fhirtypes import DateTime
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.medicationstatement import MedicationStatement
from fhir.resources.R4B.meta import Meta
from fhir.resources.R4B.period import Period
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.timing import Timing, TimingRepeat
from slugify import slugify
from structlog import get_logger

from ahd2fhir import config
from ahd2fhir.utils.fhir_utils import sha256_of_identifier

log = get_logger()

MEDICATION_STATEMENT_PROFILE = (
    "https://www.medizininformatik-initiative.de/"
    + "fhir/core/modul-medikation/StructureDefinition/MedicationStatement"
)
STATUS_MAPPING = {
    "null": "unknown",
    "ADMISSION": "active",
    "ALLERGY": "unknown",
    "INPATIENT": "active",
    "DISCHARGE": "active",
    "NEGATED": "not-taken",
    "CONSIDERED": "intended",
    "INTENDED": "intended",
    "FAMILY": "unknown",
    "CONDITIONING_TREATMENT": "active",
}
WHEN_MAPPING = {
    "morning": "MORN",
    "midday": "NOON",
    "evening": "EVE",
    "atNight": "NIGHT",
}

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

FHIR_SYSTEMS = config.FhirSystemSettings()


def get_fhir_medication_statement(val, document_reference: DocumentReference):
    """
    Returns a list of {statement: ..., medication: ...} tuples
    """
    return get_medication_statement_from_annotation(
        annotation=val, document_reference=document_reference
    )


def get_medication_statement_from_annotation(
    annotation, document_reference: DocumentReference
) -> MedicationStatement | None:
    annotation_type_lowercase = annotation["type"].replace(".", "-").lower()
    identifier_system = (
        f"{FHIR_SYSTEMS.ahd_to_fhir_base_url}/identifiers/{annotation_type_lowercase}"
    )

    if annotation["status"] == "NEGATED" or annotation["status"] == "FAMILY":
        log.warning("annotation status is NEGATED or FAMILY. Ignoring.")
        return None

    atc_codes = annotation.get("atcCodes", [])

    if atc_codes is None or len(atc_codes) == 0:
        log.warn("No ATC code set for medication. Not mapping")
        return None

    drugs = annotation["drugs"]

    if len(drugs) > 1:
        log.warning(
            "More than one drugs entry found. Defaulting to only the first entry."
        )

    drug = drugs[0]
    druq_unique_id = slugify(drug["ingredient"]["uniqueID"])

    medication_statement = MedicationStatement.construct(
        status=STATUS_MAPPING.get(annotation["status"], "unknown"),
        medicationCodeableConcept=CodeableConcept.construct(),
    )

    medication_statement.meta = Meta.construct()
    medication_statement.meta.profile = [MEDICATION_STATEMENT_PROFILE]

    medication_statement.subject = document_reference.subject
    medication_statement.context = (
        document_reference.context.encounter[0]
        if document_reference.context is not None
        else None
    )
    document_identifier_value = (
        document_reference.identifier[0].value
        if document_reference.identifier is not None
        else None
    )

    statement_identifier = Identifier.construct()
    statement_identifier.system = identifier_system
    statement_identifier.value = (
        f"{druq_unique_id}" + f"_{document_identifier_value}" + f"_{annotation['id']}"
    )

    medication_statement.identifier = [statement_identifier]
    medication_statement.id = sha256_of_identifier(statement_identifier)

    medication_statement.effectiveDateTime__ext = DATA_ABSENT_EXTENSION_UNKNOWN
    medication_statement.dateAsserted = document_reference.date

    dosage = get_medication_dosage_from_annotation(annotation)
    if dosage is not None:
        medication_statement.dosage = [dosage]

    codings = []
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
            log.warn(
                f"Unable to extract version from atcCode source: {atc_code['source']}"
            )

        codings.append(coding)

    medication_statement.medicationCodeableConcept.coding = codings

    return medication_statement


def get_medication_interval_from_annotation(
    annotation,
) -> Union[Period, DateTime, None]:
    interval = Period()

    if annotation["date"] is None:
        return None

    if annotation["date"]["kind"] == "DATEINTERVAL":
        interval.start = DateTime.validate(annotation["date"]["startDate"])
        interval.end = DateTime.validate(annotation["date"]["endDate"])
        return interval

    return DateTime.validate(annotation["date"]["value"])


def get_medication_dosage_from_annotation(annotation) -> Dosage:
    dosage = Dosage.construct()

    drug = annotation["drugs"][0]
    if (
        drug is None
        or "ingredient" not in drug
        or drug["ingredient"] is None
        or "strength" not in drug
        or drug["strength"] is None
        or "value" not in drug["strength"]
        or "unit" not in drug["strength"]
        or drug["strength"]["value"] is None
        or drug["strength"]["unit"] is None
    ):
        return None

    dosage.text = drug["coveredText"]

    quantity_value = drug["strength"]["value"]
    quantity_value = round(quantity_value, 5)

    quantity = Quantity.construct()
    quantity.value = quantity_value
    quantity.unit = drug["strength"]["unit"]
    quantity.code = drug["strength"]["unit"]
    quantity.system = "http://unitsofmeasure.org"

    dose_and_rate = DosageDoseAndRate.construct()
    dose_and_rate.doseQuantity = quantity
    dosage.doseAndRate = [dose_and_rate]

    dose_frequency = None
    if "doseFrequency" in annotation:
        dose_frequency = annotation["doseFrequency"]
    if dose_frequency is None or "interval" not in dose_frequency:
        return dosage

    dosage.asNeededBoolean = dose_frequency["interval"] == "asneeded"

    timing = Timing.construct()
    repeat = TimingRepeat.construct()

    if dose_frequency["interval"] == "daytime":
        day_times = ["morning", "midday", "evening", "atNight"]
        day_time = []
        for time in day_times:
            if time in dose_frequency:
                day_time.append(WHEN_MAPPING.get(time))
        repeat.when = day_time
    elif dose_frequency["interval"] == "weektime":
        weekdays = ["mon", "tues", "wednes", "thurs", "fri", "satur", "sun"]
        days_of_week = []
        for day in weekdays:
            if day + "day" in dose_frequency:
                days_of_week.append(day + "day")
        repeat.dayOfWeek = days_of_week

    timing.repeat = repeat
    dosage.timing = timing

    return dosage
