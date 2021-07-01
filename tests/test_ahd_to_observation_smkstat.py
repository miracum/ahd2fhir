import json

import pytest

from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_observation,
)
from tests.utils import get_empty_document_reference

AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS = [
    ("payload_1.json", 3),
    ("payload_2.json", 0),
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
        if val["type"] == UKLFR_TYPE_SMKSTAT:
            mapped_condition = get_fhir_observation(val, get_empty_document_reference())
            if mapped_condition is not None:
                conditions.append(mapped_condition)
    assert len(conditions) == expected_number_of_conditions


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_mapped_condition_coding_should_set_userselected_to_false(ahd_json_path, _):
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    conditions = []
    for val in ahd_payload:
        if val["type"] == UKLFR_TYPE_SMKSTAT:
            mapped_condition = get_fhir_observation(val, get_empty_document_reference())
            if mapped_condition is not None:
                conditions.append(mapped_condition)

    for c in conditions:
        assert all(coding.userSelected is False for coding in c.code.coding)


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_mapped_condition_coding_includes_snomed_and_loin(ahd_json_path, _):
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    conditions = []
    for val in ahd_payload:
        if val["type"] == UKLFR_TYPE_SMKSTAT:
            mapped_condition = get_fhir_observation(val, get_empty_document_reference())
            if mapped_condition is not None:
                conditions.append(mapped_condition)

    for c in conditions:
        assert c.valueCodeableConcept.coding[0].system == "http://loinc.org"
        assert c.valueCodeableConcept.coding[1].system == "http://snomed.info/sct"
