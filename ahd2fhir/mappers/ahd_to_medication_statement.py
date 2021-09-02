from hashlib import sha256
from typing import List, Union

from fhir.resources.documentreference import DocumentReference
from fhir.resources.dosage import Dosage, DosageDoseAndRate
from fhir.resources.fhirprimitiveextension import FHIRPrimitiveExtension
from fhir.resources.fhirtypes import DateTime
from fhir.resources.identifier import Identifier
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.meta import Meta
from fhir.resources.period import Period
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.timing import Timing, TimingRepeat
from structlog import get_logger

from ahd2fhir.mappers.ahd_to_medication import get_medication_from_annotation

log = get_logger()

AHD_TYPE_MEDICATION = "de.averbis.types.health.Medication"
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


def get_fhir_medication_statement(val, document_reference: DocumentReference):
    """
    Returns a list of {statement: ..., medication: ...} tuples
    """
    return get_medication_statement_from_annotation(
        annotation=val, document_reference=document_reference
    )


def get_medication_statement_from_annotation(
    annotation, document_reference: DocumentReference
):
    results = []
    for drug in annotation["drugs"]:
        if drug is None or "ingredient" not in drug or drug["ingredient"] is None:
            continue
        if annotation["status"] == "NEGATED" or annotation["status"] == "FAMILY":
            log.warning("annotation status is NEGATED or FAMILY. Ignoring.")
            continue

        medication_statement = MedicationStatement.construct(
            status=STATUS_MAPPING.get(annotation["status"], "unknown")
        )

        medication = get_medication_from_annotation(annotation)
        medication_reference = Reference.construct()
        medication_reference.type = f"{medication.resource_type}"
        medication_reference.identifier = medication.identifier[0]
        medication_reference.reference = f"{medication.resource_type}/{medication.id}"
        medication_statement.medicationReference = medication_reference

        medication_statement.subject = document_reference.subject
        medication_statement.context = (
            document_reference.context.encounter[0]
            if document_reference.context is not None
            else None
        )

        medication_identifier_value = (
            medication.identifier[0].value
            if medication.identifier is not None
            else None
        )

        document_identifier_value = (
            document_reference.identifier[0].value
            if document_reference.identifier is not None
            else None
        )

        statement_identifier = Identifier.construct()
        statement_identifier.system = (
            "https://fhir.miracum.org/nlp/identifiers/"
            + f"{annotation['type'].replace('.', '-').lower()}"
        )
        statement_identifier.value = (
            f"{medication_identifier_value}"
            + f"_{document_identifier_value}"
            + f"_{annotation['id']}"
        )

        medication_statement.identifier = [statement_identifier]

        medication_statement.id = sha256(
            f"{statement_identifier.system}"
            f"|{statement_identifier.value}".encode("utf-8")
        ).hexdigest()

        medication_statement.effectiveDateTime__ext = DATA_ABSENT_EXTENSION_UNKNOWN

        medication_statement.dateAsserted = document_reference.date

        dosage = get_medication_dosage_from_annotation(annotation)
        if dosage is not None:
            medication_statement.dosage = [dosage]

        medication_statement.meta = Meta.construct()
        medication_statement.meta.profile = [MEDICATION_STATEMENT_PROFILE]
        results.append({"statement": medication_statement, "medication": medication})
    return results


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

    dose_and_rate = DosageDoseAndRate.construct()
    quantity = Quantity.construct()

    quantity.value = drug["strength"]["value"]
    quantity.unit = drug["strength"]["unit"]

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


def deduplicate_resources(resources: List[dict]):
    medication_results = []
    medication_statement_results = []
    medication_statement_lists = resources
    # medication_statement_list = [[{medication: ..., statement: ...}],]
    for medication_statement_dict in medication_statement_lists:
        medication_results.append(medication_statement_dict["medication"])
        medication_statement_results.append(medication_statement_dict["statement"])

    # de-duplicate any Medication and MedicationStatement resources
    medication_resources_unique = {m.id: m for m in medication_results}.values()
    medication_statements_unique = {
        m.id: m for m in medication_statement_results
    }.values()
    print(medication_statements_unique)
    print(medication_resources_unique)
    print(type(list(medication_statements_unique)))
    result = [*medication_statements_unique, *medication_resources_unique]
    print(result)
    return result
