from fhir.resources.documentreference import DocumentReference

from ahd2fhir.mappers import ahd_to_observation_kidney_stone as ks
from ahd2fhir.mappers import ahd_to_observation_smkstat as smk

mapper_functions = {
    smk.AHD_TYPE: [smk.get_fhir_resources],
    ks.AHD_TYPE: [ks.get_fhir_resources],
}


def custom_mappers(val: dict, document_reference: DocumentReference) -> list:
    results = []
    if (mappers := mapper_functions.get(val["type"], None)) is not None:
        for mapper in mappers:
            results.extend(mapper(val, document_reference))
    return results
