import json

import pytest

from ahd2fhir.mappers.ahd_to_observation_kidney_stone import (
    UKLFR_TYPE_KIDNEY_STONE,
    get_fhir_kidney_stone_observations,
)
from tests.utils import get_empty_document_reference

AHD_PAYLOADS_EXPECTED_NUMBER_OF_OBSERVATIONS = [
    ("payload_1.json", 3),
    ("payload_2.json", 0),
]


@pytest.mark.parametrize(
    "ahd_json_path,expected_number_of_observations",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_OBSERVATIONS,
)
def test_maps_to_expected_number_of_condition_resources(
    ahd_json_path, expected_number_of_observations
):
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    observations = []
    for val in ahd_payload:
        if val["type"] == UKLFR_TYPE_KIDNEY_STONE:
            mapped_observation = get_fhir_kidney_stone_observations(
                val, get_empty_document_reference()
            )
            if mapped_observation is not None:
                observations.append(mapped_observation)
    assert len(observations) == expected_number_of_observations


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_OBSERVATIONS,
)
def test_mapped_observation_coding_should_set_userselected_to_false(ahd_json_path, _):
    with open(f"tests/resources/ahd/{ahd_json_path}") as file:
        ahd_payload = json.load(file)

    observations = []
    for val in ahd_payload:
        if val["type"] == UKLFR_TYPE_KIDNEY_STONE:
            mapped_observation = get_fhir_kidney_stone_observations(
                val, get_empty_document_reference()
            )
            if mapped_observation is not None:
                observations.append(mapped_observation)

    for c in observations:
        assert all(coding.userSelected is False for coding in c[0].code.coding)
