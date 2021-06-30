from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_observation,
)


def custom_mappers(val, document_reference):
    if val["type"] == UKLFR_TYPE_SMKSTAT:
        smkstat_observations = get_fhir_observation(val, document_reference)
        if smkstat_observations is not None:
            return smkstat_observations
    return []
