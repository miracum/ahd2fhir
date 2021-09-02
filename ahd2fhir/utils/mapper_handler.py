import dataclasses
from typing import Callable

import structlog
from fhir.resources.resource import Resource

from ahd2fhir.config import Settings
from ahd2fhir.mappers.ahd_to_condition import AHD_TYPE_DIAGNOSIS, get_fhir_condition
from ahd2fhir.mappers.ahd_to_medication_statement import (
    AHD_TYPE_MEDICATION,
    deduplicate_resources,
    get_fhir_medication_statement,
)
from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_resources,
)
from ahd2fhir.utils.device_builder import AHD_TYPE_DOCUMENT_ANNOTATION, build_device

log = structlog.get_logger()


@dataclasses.dataclass
class MapperBase:
    name: str
    config: Settings
    ahd_type: str
    mapper_function: Callable
    deduplicate_function: Callable = lambda x: x

    def get_resources(self, ahd_response_entry, doc_ref):
        return self.mapper_function(ahd_response_entry, doc_ref)

    def deduplicate_resources(self, resources):
        return self.deduplicate_function(resources)

    def enabled(self) -> bool:
        return True if self.ahd_type in self.config.mappers_enabled else False

    def __repr__(self):
        return self.name


class MapperHandler:
    def __init__(self, config):
        self.mappers = [
            MapperBase(
                name="SmokingStatus",
                config=config,
                ahd_type=UKLFR_TYPE_SMKSTAT,
                mapper_function=get_fhir_resources,
            ),
            MapperBase(
                name="DeviceMapper",
                config=config,
                ahd_type=AHD_TYPE_DOCUMENT_ANNOTATION,
                mapper_function=build_device,
            ),
            MapperBase(
                name="ConditionMapper",
                config=config,
                ahd_type=AHD_TYPE_DIAGNOSIS,
                mapper_function=get_fhir_condition,
            ),
            MapperBase(
                name="MedicationMapper",
                config=config,
                ahd_type=AHD_TYPE_MEDICATION,
                mapper_function=get_fhir_medication_statement,
                deduplicate_function=deduplicate_resources,
            ),
        ]
        log.info(f"Enabled mappers: {[m for m in self.mappers if m.enabled()]}")

    def get_mappings(self, averbis_result, doc_ref):
        total_results = []
        for mapper in [m for m in self.mappers if m.enabled()]:
            mapper_results = []
            for val in averbis_result:
                if val["type"] == mapper.ahd_type:
                    if (results := mapper.get_resources(val, doc_ref)) is not None:
                        if isinstance(results, list):
                            mapper_results.extend(results)
                        if isinstance(results, Resource):
                            mapper_results.append(results)

            mapper_results = mapper.deduplicate_resources(mapper_results)
            total_results.extend(mapper_results)
        print([[type(r)] for r in total_results])
        return total_results

    def get_ahd_types(self):
        return [m.ahd_type for m in self.mappers]
