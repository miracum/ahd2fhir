import pytest

from ahd2fhir.mappers.ahd_to_observation_kidney_stone import (
    AHD_TYPE,
    get_fhir_resources,
)
from tests.utils import map_resources

AHD_PAYLOADS_EXPECTED_NUMBER_OF_OBSERVATIONS = [
    ("payload_1_v5.json", 3),
    ("payload_2.json", 0),
]


@pytest.mark.parametrize(
    "ahd_json_path,expected_number_of_observations",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_OBSERVATIONS,
)
def test_maps_to_expected_number_of_condition_resources(
    ahd_json_path, expected_number_of_observations
):
    observations = map_resources(ahd_json_path, AHD_TYPE, get_fhir_resources)
    assert len(observations) == expected_number_of_observations


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_OBSERVATIONS,
)
def test_mapped_observation_coding_should_set_userselected_to_false(ahd_json_path, _):
    observations = map_resources(ahd_json_path, AHD_TYPE, get_fhir_resources)
    for o in observations:
        assert all(coding.userSelected is False for coding in o[0].code.coding)
