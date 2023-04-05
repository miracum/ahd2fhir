import json

import pytest
from fhir.resources.documentreference import DocumentReferenceContext

from ahd2fhir.mappers.ahd_to_condition import get_fhir_condition
from ahd2fhir.utils.resource_handler import AHD_TYPE_DIAGNOSIS
from tests.utils import get_empty_document_reference

AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS = [
    ("payload_1_v5.json", 13),
    ("payload_2.json", 7),
]


@pytest.mark.parametrize(
    "ahd_json_path,expected_number_of_conditions",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_maps_to_expected_number_of_condition_resources(
    ahd_json_path, expected_number_of_conditions
):
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    conditions = []
    for val in ahd_payload:
        if val["type"] == AHD_TYPE_DIAGNOSIS:
            mapped_condition = get_fhir_condition(val, get_empty_document_reference())
            if mapped_condition is not None:
                conditions.append(mapped_condition)

    assert len(conditions) == expected_number_of_conditions


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_mapped_condition_coding_should_set_userselected_to_false(ahd_json_path, _):
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload_2 = json.load(file)

    conditions_2 = []
    for val in ahd_payload_2:
        if val["type"] == AHD_TYPE_DIAGNOSIS:
            mapped_condition_2 = get_fhir_condition(val, get_empty_document_reference())
            if mapped_condition_2 is not None:
                conditions_2.append(mapped_condition_2)

    for c in conditions_2:
        assert all(coding.userSelected is False for coding in c.code.coding)


def test_annotations_belonging_to_family_history_are_ignored():
    ahd_response = {"type": "de.averbis.types.health.Diagnosis", "belongsTo": "FAMILY"}

    condition = get_fhir_condition(ahd_response, get_empty_document_reference())

    assert condition is None


def test_sets_the_condition_encounter_to_the_context_from_the_documentreference():
    ahd_response = {
        "type": "de.averbis.types.health.Diagnosis",
        "conceptId": "R53",
        "source": "ICD10GM_2020",
    }
    doc_ref = get_empty_document_reference()
    doc_ref.context = DocumentReferenceContext(
        **{
            "encounter": [{"reference": "Encounter/e2216331600"}],
            "period": {
                "end": "2020-03-18T00:55:09+00:00",
                "start": "2019-02-23T09:39:31+00:00",
            },
            "sourcePatientInfo": {"reference": "Patient/p3480585566"},
        }
    )

    condition = get_fhir_condition(ahd_response, doc_ref)

    assert condition.encounter.reference == "Encounter/e2216331600"
