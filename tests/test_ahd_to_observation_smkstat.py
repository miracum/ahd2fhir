import pytest
from pathlib import Path

from ahd2fhir.mappers.ahd_to_observation_smkstat import AHD_TYPE, get_fhir_resources
from tests.utils import map_resources

AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS = [
    ("payload_1_v5.json", 3),
    ("payload_2.json", 0),
]


@pytest.mark.parametrize(
    "ahd_json_path,expected_number_of_conditions",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_maps_to_expected_number_of_condition_resources(
    ahd_json_path, expected_number_of_conditions
):
    observations = map_resources(ahd_json_path, AHD_TYPE, get_fhir_resources)
    assert len(observations) == expected_number_of_conditions


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_mapped_condition_coding_should_set_userselected_to_false(ahd_json_path, _):
    observations = [
        o
        for obs in map_resources(ahd_json_path, AHD_TYPE, get_fhir_resources)
        for o in obs
    ]
    for o in observations:
        assert all(coding.userSelected is False for coding in o.code.coding)


@pytest.mark.parametrize(
    "ahd_json_path,_",
    AHD_PAYLOADS_EXPECTED_NUMBER_OF_CONDITIONS,
)
def test_mapped_condition_coding_includes_snomed_and_loin(ahd_json_path, _):
    observations = [
        o
        for obs in map_resources(ahd_json_path, AHD_TYPE, get_fhir_resources)
        for o in obs
    ]

    for o in observations:
        assert o.valueCodeableConcept.coding[0].system == "http://loinc.org"
        assert o.valueCodeableConcept.coding[1].system == "http://snomed.info/sct"

@pytest.mark.parametrize('case_dir', list(Path('tests/test_cases').iterdir()))
def test_snapshot(case_dir, snapshot):

    ahd_json_path = "\\payload.json"

    resources = []

    for res in map_resources(ahd_json_path, AHD_TYPE, get_fhir_resources, ahd_folder_path=case_dir):
        for r in res:
            r.id = 'test'
            resources.append(r.json())    

    snapshot.snapshot_dir = case_dir
    # for i in len(resources):
    #     snapshot.assert_match(resources[i], 'output_observation_smkstat_[i].txt')
    snapshot.assert_match(resources[0], 'output_observation_smkstat.json')
