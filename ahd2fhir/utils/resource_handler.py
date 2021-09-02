import logging
from typing import List

import structlog
import tenacity
from averbis import Pipeline
from fhir.resources.bundle import Bundle
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.documentreference import DocumentReference
from prometheus_client import Counter, Histogram, Summary
from tenacity.after import after_log

from ahd2fhir.utils.bundle_builder import BundleBuilder
from ahd2fhir.utils.fhir_utils import _build_composition, _extract_text_from_resource

MAPPING_FAILURES_COUNTER = Counter("mapping_failures", "Exceptions during mapping")
MAPPING_DURATION_SUMMARY = Histogram(
    "map_duration_seconds",
    "Time spent mapping",
    buckets=(
        0.05,
        0.1,
        0.5,
        1.0,
        2.0,
        3.0,
        5.0,
        8.0,
        13.0,
        21.0,
        34.0,
        55.0,
        "inf",
    ),
)
EXTRACTED_RESOURCES_COUNT_SUMMARY = Summary(
    "extracted_resources", "Number of extracted resources for each processed document"
)
DOCUMENT_LENGTH_SUMMARY = Summary(
    "document_length",
    "Length of each processed document's text in charactes",
)

DISCHARGE_SUMMARY_CONCEPT_TEXT = (
    "Clinical document Kind of document from LOINC Document Ontology"
)
DISCHARGE_SUMMARY_CONCEPT = CodeableConcept(
    **{
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "74477-1",
                "display": DISCHARGE_SUMMARY_CONCEPT_TEXT,
            },
        ],
        "text": DISCHARGE_SUMMARY_CONCEPT_TEXT,
    }
)

AHD_TYPE_DOCUMENT_ANNOTATION = "de.averbis.types.health.DocumentAnnotation"
AHD_TYPE_MEDICATION = "de.averbis.types.health.Medication"
AHD_TYPE_DIAGNOSIS = "de.averbis.types.health.Diagnosis"

log = structlog.get_logger()


class TransientError(Exception):
    pass


class ResourceHandler:
    def __init__(self, averbis_pipeline: Pipeline, mapper_handler):
        self.pipeline = averbis_pipeline
        self.bundle_builder = BundleBuilder()
        self.mapper_handler = mapper_handler

    @MAPPING_FAILURES_COUNTER.count_exceptions()
    @MAPPING_DURATION_SUMMARY.time()
    def handle_documents(self, document_references: List[DocumentReference]) -> Bundle:
        """
        Process a list of DocumentReferences
        """
        all_resources = []
        bundle_id = None
        for document_reference in document_references:
            resources_from_document = self._process_documentreference(
                document_reference
            )
            composition = _build_composition(
                document_reference, resources_from_document
            )

            bundle_id = composition.id

            all_resources.extend(resources_from_document)
            all_resources.append(composition)

            EXTRACTED_RESOURCES_COUNT_SUMMARY.observe(len(all_resources))

        result_bundle = self.bundle_builder.build_from_resources(
            all_resources, bundle_id
        )

        return result_bundle

    def handle_bundle(self, bundle: Bundle):
        """
        Process all FHIR DocumentReference resources from a given bundle
        """
        document_references = []
        for entry in bundle.entry:
            if entry.resource.resource_type == "DocumentReference":
                document_references.append(entry.resource)

        return self.handle_documents(document_references)

    def _process_documentreference(self, document_reference: DocumentReference):
        log = structlog.get_logger().bind(
            document_id=f"{document_reference.get_resource_type()}/"
            + f"{document_reference.id}"
        )

        # Text extraction and text analysis
        (text, content_type, lang) = _extract_text_from_resource(document_reference)

        DOCUMENT_LENGTH_SUMMARY.observe(len(text))

        averbis_result = None

        try:
            averbis_result = self._perform_text_analysis(
                text=text, mime_type=content_type, lang=lang
            )
        except Exception as exc:
            log.exception(exc)
            log.error("Failed to perform text analysis", error=exc)
            raise TransientError(exc)

        total_results = []

        # Building FHIR resources as results
        # medication_statement_lists = []

        mh_results = self.mapper_handler.get_mappings(
            averbis_result, document_reference
        )
        total_results.extend(mh_results)
        # for val in averbis_result:
        #     if val["type"] == AHD_TYPE_MEDICATION:
        #         statement = ahd_to_medication_statement.get_fhir_medication_statement(
        #             val, document_reference
        #         )
        #         if statement is not None:
        #             medication_statement_lists.append(statement)

        # medication_results = []
        # medication_statement_results = []
        # # medication_statement_list = [[{medication: ..., statement: ...}],]
        # for medication_statement_list in medication_statement_lists:
        #     for medication_statement_dict in medication_statement_list:
        #         medication_results.append(medication_statement_dict["medication"])
        #         medication_statement_results.append(
        #             medication_statement_dict["statement"]
        #         )
        #
        # # de-duplicate any Medication and MedicationStatement resources
        # medication_resources_unique = {m.id: m for m in medication_results}.values()
        # medication_statements_unique = {
        #     m.id: m for m in medication_statement_results
        # }.values()
        #
        # total_results.extend(medication_resources_unique)
        # total_results.extend(medication_statements_unique)

        return total_results

    @tenacity.retry(
        stop=tenacity.stop.stop_after_attempt(10),
        wait=tenacity.wait.wait_fixed(5)
        + tenacity.wait.wait_random_exponential(multiplier=1, max=30),
        after=after_log(logging.getLogger(), logging.WARNING),
        reraise=True,
    )
    def _perform_text_analysis(
        self, text: str, mime_type: str = "text/plain", lang: str = None
    ):
        types = ",".join([*self.mapper_handler.get_ahd_types()])
        analyse_args = {"language": lang, "annotation_types": types}

        try:
            if mime_type == "text/html":
                return self.pipeline.analyse_html(text, **analyse_args)
            else:
                return self.pipeline.analyse_text(text, **analyse_args)
        except Exception as exc:
            log.exception(exc)
            log.error("Text analysis failed")
            raise exc
