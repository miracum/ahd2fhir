import dataclasses
from abc import ABCMeta, abstractmethod
from pprint import pprint
from typing import Callable, Dict, List

from fhir.resources.documentreference import DocumentReference
from fhir.resources.resource import Resource

from ahd2fhir.config import Settings
from ahd2fhir.mappers.ahd_to_condition import AHD_TYPE_DIAGNOSIS, get_fhir_condition
from ahd2fhir.mappers.ahd_to_medication_statement import (
    AHD_TYPE_MEDICATION,
    get_fhir_medication_statement,
)
from ahd2fhir.mappers.ahd_to_observation_smkstat import (
    UKLFR_TYPE_SMKSTAT,
    get_fhir_resources,
)
from ahd2fhir.utils.device_builder import AHD_TYPE_DOCUMENT_ANNOTATION, build_device


class Mapper(metaclass=ABCMeta):
    """Anbstact Base Class to define an interface for fhir mapper classes"""

    def __init__(self, config):
        self.config = config

    @property
    def ahd_type(self):
        pass

    def enabled(self) -> bool:
        return True if self.ahd_type in self.config.mappers_enabled else False

    @abstractmethod
    def get_resources(
        self, ahd_response_entry: Dict, doc_ref: DocumentReference
    ) -> List[Resource]:
        """Calls the real mapper function. Must return list of Resources"""
        pass

    @property
    @abstractmethod
    def deduplicate_resources(resources: List[Resource]):
        """Method to deduplicate Resources"""
        pass

    def __repr__(self):
        return self.__class__.__name__


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


class SmokingStatusMapper(Mapper):
    ahd_type = UKLFR_TYPE_SMKSTAT

    def get_resources(self, ahd_response_entry, doc_ref) -> List[Resource]:
        return get_fhir_resources(ahd_response_entry, doc_ref)

    @staticmethod
    def deduplicate_resources(resources):
        return resources


class DeviceMapper(Mapper):
    ahd_type = AHD_TYPE_DOCUMENT_ANNOTATION

    def get_resources(self, ahd_response_entry, doc_ref) -> List[Resource]:
        return [build_device(ahd_response_entry)]

    @staticmethod
    def deduplicate_resources(resources: List[Resource]):
        return resources

    def enabled(self):
        return True


class ConditionMapper(Mapper):
    ahd_type = AHD_TYPE_DIAGNOSIS

    def get_resources(self, ahd_response_entry, doc_ref) -> List[Resource]:
        return get_fhir_condition(ahd_response_entry, doc_ref)

    @staticmethod
    def deduplicate_resources(resources: List[Resource]):
        return resources


class MedicationMapper(Mapper):
    ahd_type = AHD_TYPE_MEDICATION

    def get_resources(self, ahd_response_entry, doc_ref) -> List[Resource]:
        return get_fhir_medication_statement(ahd_response_entry, doc_ref)

    @staticmethod
    def deduplicate_resources(resources: List[dict]):
        pprint(resources)
        medication_results = []
        medication_statement_results = []
        medication_statement_lists = resources
        # medication_statement_list = [[{medication: ..., statement: ...}],]
        for medication_statement_dict in medication_statement_lists:
            medication_results.append(medication_statement_dict["medication"])
            medication_statement_results.append(medication_statement_dict["statement"])

        # de-duplicate any Medication and MedicationStatement resources
        medication_resources_unique = {m.id: m for m in medication_results}.values()
        medication_statements_unique = {
            m.id: m for m in medication_statement_results
        }.values()
        print(medication_statements_unique)
        print(medication_resources_unique)
        print(type(list(medication_statements_unique)))
        result = [*medication_statements_unique, *medication_resources_unique]
        print(result)
        return result
