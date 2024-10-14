import datetime
import json
from decimal import Decimal

from fhir.resources.R4B.attachment import Attachment
from fhir.resources.R4B.documentreference import (
    DocumentReference,
    DocumentReferenceContent,
)
from fhir.resources.R4B.fhirtypes import DateTime
from fhir.resources.R4B.period import Period
from fhir.resources.R4B.reference import Reference

from ahd2fhir.mappers.ahd_to_medication_statement import (
    get_fhir_medication_statement,
    get_medication_dosage_from_annotation,
    get_medication_interval_from_annotation,
)
from ahd2fhir.utils.resource_handler import AHD_TYPE_MEDICATION


def get_example_payload_v6():
    with open("tests/resources/ahd/payload_1.json") as file:
        return json.load(file)


def get_empty_document_reference():
    docref = DocumentReference.construct()
    docref.status = "current"
    cnt = DocumentReferenceContent.construct()
    cnt.attachment = Attachment.construct()
    docref.content = [cnt]
    subject_ref = Reference.construct()
    subject_ref.reference = "Patient/Test"
    subject_ref.type = "Patient"
    docref.subject = subject_ref

    docref.date = DateTime.validate(datetime.datetime.now(datetime.timezone.utc))

    return docref


def test_get_medication_interval_from_annotation_for_date():
    annotation = {"date": {"kind": "DATE", "value": "2018-01-01"}}
    date = get_medication_interval_from_annotation(annotation)
    assert date is not None
    assert date.isoformat() == DateTime.validate("2018-01-01").isoformat()


def test_get_medication_intverval_from_annotation_for_date_interval():
    annotation = {
        "date": {
            "kind": "DATEINTERVAL",
            "startDate": "2018-01-01",
            "endDate": "2019-01-01",
        }
    }
    assert isinstance(get_medication_interval_from_annotation(annotation), Period)


def test_fhir_medication_v6():
    annotation_v6 = [
        a for a in get_example_payload_v6() if a["type"] == AHD_TYPE_MEDICATION
    ][0]

    statement_v6 = get_fhir_medication_statement(
        annotation_v6, get_empty_document_reference()
    )

    assert statement_v6 is not None

    assert statement_v6.json()
    assert statement_v6.status is not None
    assert statement_v6.medicationReference is None
    assert statement_v6.medicationCodeableConcept is not None


def test_get_medication_dosage_from_annotation_should_round_quantity_value():
    annotation = {
        "type": "de.averbis.types.health.Medication",
        "coveredText": "Therapie mit Piperacillin 4x4g i.v. sowie 4x500mg",
        "id": 82560,
        "administrations": ["i.v."],
        "drugs": [
            {
                "begin": 3055,
                "end": 3099,
                "type": "de.averbis.types.health.Drug",
                "coveredText": "antibiotische Therapie mit Piperacillin 4x4g",
                "id": 82561,
                "ingredient": {
                    "begin": 3055,
                    "end": 3077,
                    "type": "de.averbis.types.health.Ingredient",
                    "coveredText": "antibiotische Therapie",
                    "id": 82562,
                    "matchedTerm": "antibiotische Therapie",
                    "dictCanon": "Antibakterielle Mittel",
                    "conceptID": "255631004",
                    "source": "SNOMED-DrugClasses-DE_2023-11",
                    "uniqueID": "SNOMED-DrugClasses-DE_2023-11:255631004",
                },
                "strength": {
                    "begin": 3097,
                    "end": 3099,
                    "type": "de.averbis.types.health.Strength",
                    "coveredText": "4g",
                    "id": 82563,
                    "unit": "g",
                    "normalizedUnit": "kg",
                    "normalizedValue": 0.004,
                    "value": 1.111111111111,
                    "dimension": "[M]",
                },
            }
        ],
        "atcCodes": [
            {
                "begin": 3055,
                "end": 3099,
                "type": "de.averbis.types.health.ATCCode",
                "coveredText": "antibiotische Therapie mit Piperacillin 4x4g",
                "id": 82574,
                "dictCanon": "ANTIBIOTIKA ZUR SYSTEMISCHEN ANWENDUNG",
                "conceptID": "J01",
                "source": "ATCA_2024",
            }
        ],
    }

    dosage = get_medication_dosage_from_annotation(annotation)

    assert len(dosage.doseAndRate) == 1
    assert dosage.doseAndRate[0].doseQuantity.system == "http://unitsofmeasure.org"
    assert dosage.doseAndRate[0].doseQuantity.unit == "g"
    assert dosage.doseAndRate[0].doseQuantity.value == Decimal("1.11111")
