import dataclasses
from typing import Callable

import structlog
from fhir.resources.resource import Resource

from ahd2fhir.config import Settings
from ahd2fhir.mappers.ahd_to_condition import AHD_TYPE_DIAGNOSIS, get_fhir_condition
from ahd2fhir.mappers.ahd_to_device import AHD_TYPE_DOCUMENT_ANNOTATION, build_device
from ahd2fhir.mappers.ahd_to_list import get_fhir_list_resources
from ahd2fhir.mappers.ahd_to_medication_statement import (
    AHD_TYPE_MEDICATION,
    deduplicate_resources,
    get_fhir_medication_statement,
)
from ahd2fhir.mappers.ahd_to_observation_kidney_stone import (
    UKLFR_TYPE_KIDNEY_STONE,
    get_fhir_kidney_stones,
)
from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_smoking_status,
)

log = structlog.get_logger()


@dataclasses.dataclass
class Mapper:
    name: str
    config: Settings
    ahd_type: str
    mapper_function: Callable
    deduplicate_function: Callable = lambda x: x
    handle_all_annotations: bool = False

    def get_resources(self, ahd_response_entry, doc_ref):
        return self.mapper_function(ahd_response_entry, doc_ref)

    def deduplicate_resources(self, resources):
        return self.deduplicate_function(resources)

    def __repr__(self):
        return self.name


class MapperHandler:
    def __init__(self, config: Settings):
        mappers = [
            Mapper(
                name="DeviceMapper",
                config=config,
                ahd_type=AHD_TYPE_DOCUMENT_ANNOTATION,
                mapper_function=build_device,
            ),
            Mapper(
                name="ConditionMapper",
                config=config,
                ahd_type=AHD_TYPE_DIAGNOSIS,
                mapper_function=get_fhir_condition,
            ),
            Mapper(
                name="MedicationMapper",
                config=config,
                ahd_type=AHD_TYPE_MEDICATION,
                mapper_function=get_fhir_medication_statement,
                deduplicate_function=deduplicate_resources,
            ),
            Mapper(
                name="ListMapper",
                config=config,
                ahd_type=AHD_TYPE_MEDICATION,
                mapper_function=get_fhir_list_resources,
                handle_all_annotations=True,
            ),
            Mapper(
                name="KidneyStoneMapper",
                config=config,
                ahd_type=UKLFR_TYPE_KIDNEY_STONE,
                mapper_function=get_fhir_kidney_stones,
            ),
            Mapper(
                name="SmokingStatusMapper",
                config=config,
                ahd_type=UKLFR_TYPE_SMKSTAT,
                mapper_function=get_fhir_smoking_status,
            ),
        ]
        self.enabled_mappers = [m for m in mappers if m.name in config.enabled_mappers]
        log.info(f"Enabled mappers: {self.enabled_mappers}")

    def get_mappings(self, averbis_result, doc_ref):
        total_results = []
        for mapper in self.enabled_mappers:
            if mapper.handle_all_annotations:
                mapper_results = mapper.get_resources(averbis_result, doc_ref)
            else:
                mapper_results = []
                for val in averbis_result:
                    if val["type"] != mapper.ahd_type:
                        continue
                    if (results := mapper.get_resources(val, doc_ref)) is not None:
                        if isinstance(results, list):
                            mapper_results.extend(results)
                        if isinstance(results, Resource):
                            mapper_results.append(results)

            mapper_results = mapper.deduplicate_resources(mapper_results)
            total_results.extend(mapper_results)
        return total_results

    def get_ahd_types(self):
        return [m.ahd_type for m in self.enabled_mappers]
