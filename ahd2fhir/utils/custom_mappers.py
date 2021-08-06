from abc import ABCMeta, abstractmethod
from typing import Dict, List

from fhir.resources.documentreference import DocumentReference
from fhir.resources.resource import Resource

#
# def custom_mappers(val: dict, document_reference: DocumentReference) -> list:
#     results = []
#     if (mappers := mapper_functions.get(val["type"], None)) is not None:
#         for mapper in mappers:
#             results.extend(mapper(val, document_reference))
#     return results
from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_resources,
)
from ahd2fhir.utils.device_builder import AHD_TYPE_DOCUMENT_ANNOTATION, build_device

#
# mapper_functions = {
#     smk.AHD_TYPE: [smk.get_fhir_resources],
#     ks.AHD_TYPE: [ks.get_fhir_resources],
# }


class Mapper(metaclass=ABCMeta):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def get_resources(
        self, ahd_response_entry: Dict, doc_ref: DocumentReference
    ) -> List[Resource]:
        pass

    @staticmethod
    @property
    @abstractmethod
    def deduplicate_resource(resources: List[Resource]):
        pass

    @property
    def ahd_type(self):
        pass

    def enabled(self):
        return True if self.type in self.config.types_enabled else False


class SmokingStatusMapper(Mapper):
    ahd_type = UKLFR_TYPE_SMKSTAT

    def get_resources(self, ahd_response_entry, doc_ref) -> List[Resource]:
        return get_fhir_resources(ahd_response_entry, doc_ref)

    def deduplicate_resources(resources):
        return resources


class DeviceMapper(Mapper):
    ahd_type = AHD_TYPE_DOCUMENT_ANNOTATION

    def get_resources(self, ahd_response_entry, doc_ref) -> List[Resource]:
        return [build_device(ahd_response_entry)]

    def deduplicate_resources(resources: List[Resource]):
        return resources
