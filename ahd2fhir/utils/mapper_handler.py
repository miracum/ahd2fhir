import structlog
from fhir.resources.resource import Resource

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
from ahd2fhir.utils.custom_mappers import MapperBase
from ahd2fhir.utils.device_builder import AHD_TYPE_DOCUMENT_ANNOTATION, build_device

log = structlog.get_logger()


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
            MapperBase(
                "DeviceMapper", config, AHD_TYPE_DOCUMENT_ANNOTATION, build_device
            ),
            MapperBase(
                "ConditionMapper", config, AHD_TYPE_DIAGNOSIS, get_fhir_condition
            ),
            MapperBase(
                "MedicationMapper",
                config,
                AHD_TYPE_MEDICATION,
                get_fhir_medication_statement,
                deduplicate_resources,
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
            # print(mapper, mapper_results)
            total_results.extend(mapper_results)
        print([[type(r)] for r in total_results])
        return total_results

    def get_ahd_types(self):
        return [m.ahd_type for m in self.mappers]
