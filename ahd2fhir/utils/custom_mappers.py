from fhir.resources.documentreference import DocumentReference

from ahd2fhir.mappers.ahd_to_observation_kidney_stone import (
    UKLFR_TYPE_KIDNEY_STONE,
    get_fhir_kidney_stone_observations,
)
from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_observation,
)


def custom_mappers(val: dict, document_reference: DocumentReference) -> list:
    results = []
    # UKLFR Smoking Status mapper
    if val["type"] == UKLFR_TYPE_SMKSTAT:
        smkstat_observations = get_fhir_observation(val, document_reference)
        if smkstat_observations is not None:
            results.extend(smkstat_observations)

    # UKLFR KidneyStone mapper
    if val["type"] == UKLFR_TYPE_KIDNEY_STONE:
        ks_observations = get_fhir_kidney_stone_observations(val, document_reference)
        if ks_observations not in [None, []]:
            results.extend(ks_observations)

    return results
