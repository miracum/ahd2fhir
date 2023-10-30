import base64
import logging
import os
from datetime import datetime, timezone
from typing import List, Tuple

import structlog
import tenacity
from averbis import Pipeline
from bs4 import BeautifulSoup
from fhir.resources.bundle import Bundle
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.composition import Composition, CompositionSection
from fhir.resources.documentreference import DocumentReference
from fhir.resources.fhirtypes import DateTime
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.resource import Resource
from prometheus_client import Counter, Histogram, Summary
from tenacity.after import after_log

from ahd2fhir.mappers import ahd_to_condition, ahd_to_list, ahd_to_medication_statement
from ahd2fhir.utils.bundle_builder import BundleBuilder
from ahd2fhir.utils.custom_mappers import custom_mappers, mapper_functions
from ahd2fhir.utils.device_builder import build_device
from ahd2fhir.utils.fhir_utils import sha256_of_identifier

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

DISCHARGE_SUMMARY_CONCEPT_TEXT = "Discharge summary"
DISCHARGE_SUMMARY_CONCEPT = CodeableConcept(
    **{
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "18842-5",
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
    def __init__(
        self,
        averbis_pipeline: Pipeline,
        fixed_composition_datetime: datetime | None = None,
    ):
        self.pipeline = averbis_pipeline
        self.bundle_builder = BundleBuilder()
        self.fixed_composition_datetime = fixed_composition_datetime

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
            composition = self._build_composition(
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

    def _build_composition(
        self, document_reference: DocumentReference, all_resources: List[Resource]
    ):
        composition_type = (
            document_reference.type
            if document_reference.type is not None
            else DISCHARGE_SUMMARY_CONCEPT
        )

        composition_subject = document_reference.subject
        composition_category = document_reference.category
        composition_encounter = None

        if document_reference.context is not None:
            if len(document_reference.context.encounter) > 1:
                log.warning(
                    "DocumentReference contains more than one encounter. "
                    + "Using the first."
                )
            composition_encounter = document_reference.context.encounter[0]

        composition_author = None
        composition_sections: list[CompositionSection] = []
        for resource in all_resources:
            resource_type = resource.resource_type

            if resource_type == "Device":
                author = Reference.construct()
                author.reference = f"Device/{resource.id}"
                author.type = "Device"
                composition_author = author
                continue

            # Check if no resource specific section exists ands adds it,
            # otherwise select the correct section
            if not any(
                section.title == resource_type for section in composition_sections
            ):
                resource_section = CompositionSection.construct()
                resource_section.title = resource_type
                resource_section.entry = []

                composition_sections.append(resource_section)

                ind = len(composition_sections) - 1
            else:
                ind = [
                    ind
                    for ind, section in enumerate(composition_sections)
                    if section.title == resource_type
                ][0]

            entry_reference = Reference.construct()
            entry_reference.reference = resource_type + "/" + resource.id

            composition_sections[ind].entry.append(entry_reference)

        if composition_author is None:
            composition_author = Reference(**{"display": "Averbis Health Discovery"})

        composition_identifier = (
            self._build_composition_identifier_from_documentreference(
                document_reference
            )
        )

        composition_datetime: datetime = datetime.now(tz=timezone.utc)
        if self.fixed_composition_datetime:
            composition_datetime = self.fixed_composition_datetime

        composition = Composition(
            **{
                "title": "AHD2FHIR NLP Processing Results "
                + composition_datetime.isoformat(),
                "status": "final",
                "date": DateTime.validate(composition_datetime),
                "type": composition_type,
                "identifier": composition_identifier,
                "id": sha256_of_identifier(composition_identifier),
                "subject": composition_subject,
                "category": composition_category,
                "encounter": composition_encounter,
                "author": [composition_author],
                "section": composition_sections,
            }
        )

        return composition

    def _process_documentreference(self, document_reference: DocumentReference):
        log = structlog.get_logger().bind(
            document_id=f"{document_reference.get_resource_type()}/"
            + f"{document_reference.id}"
        )

        # Text extraction and text analysis
        (text, content_type, lang) = self._extract_text_from_resource(
            document_reference
        )

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

        lists = ahd_to_list.get_fhir_list(
            annotation_results=averbis_result, document_reference=document_reference
        )
        if lists is not None:
            discharge_list = lists["DISCHARGE"]
            if discharge_list is not None:
                total_results.append(discharge_list)
            admission_list = lists["ADMISSION"]
            if admission_list is not None:
                total_results.append(admission_list)
            inpatient_list = lists["INPATIENT"]
            if inpatient_list is not None:
                total_results.append(inpatient_list)

        medication_statement_lists = []
        for val in averbis_result:
            if val["type"] == AHD_TYPE_DIAGNOSIS:
                mapped_condition = ahd_to_condition.get_fhir_condition(
                    val, document_reference
                )
                if mapped_condition is not None:
                    total_results.append(mapped_condition)

            if val["type"] == AHD_TYPE_DOCUMENT_ANNOTATION:
                device = build_device(val)
                if device is not None:
                    total_results.append(device)

            if val["type"] == AHD_TYPE_MEDICATION:
                statement = ahd_to_medication_statement.get_fhir_medication_statement(
                    val, document_reference
                )
                if statement is not None:
                    medication_statement_lists.append(statement)

            # if custom_mappers_enabled
            if os.getenv("CUSTOM_MAPPERS_ENABLED", "False").lower() in ["true", "1"]:
                total_results.extend(custom_mappers(val, document_reference))

        medication_results = []
        medication_statement_results = []
        for medication_statement_list in medication_statement_lists:
            for medication_statement_dict in medication_statement_list:
                medication_results.append(medication_statement_dict["medication"])
                medication_statement_results.append(
                    medication_statement_dict["statement"]
                )

        # de-duplicate any Medication and MedicationStatement resources
        medication_resources_unique = {m.id: m for m in medication_results}.values()
        medication_statements_unique = {
            m.id: m for m in medication_statement_results
        }.values()

        total_results.extend(medication_resources_unique)
        total_results.extend(medication_statements_unique)

        return total_results

    def _extract_text_from_resource(
        self,
        document_reference: DocumentReference,
    ) -> Tuple[str, str, str]:
        valid_content = [
            content
            for content in document_reference.content
            if content.attachment.data is not None
        ]

        if len(valid_content) == 0:
            raise ValueError(
                f"Document {document_reference.id} contains no valid content"
            )

        if len(valid_content) > 1:
            raise ValueError(
                f"Document {document_reference.id} contains more than one attachment"
            )

        content = valid_content[0]

        if content.attachment is None:
            raise ValueError(
                f"Document {document_reference.id} contains has no "
                + "content.attachment specified"
            )

        if content.attachment.contentType is None:
            raise ValueError(
                f"Document {document_reference.id} contains has no "
                + "content.attachment.contentType specified"
            )

        language = None
        if content.attachment.language:
            language = content.attachment.language.lower().split("-")[0]

        return (
            base64.b64decode(content.attachment.data).decode("utf8"),
            str(content.attachment.contentType),
            str(language),
        )

    @tenacity.retry(
        stop=tenacity.stop.stop_after_attempt(10),
        wait=tenacity.wait.wait_fixed(5)
        + tenacity.wait.wait_random_exponential(multiplier=1, max=30),
        after=after_log(logging.getLogger(), logging.WARNING),
        reraise=True,
    )
    def _perform_text_analysis(
        self, text: str, mime_type: str = "text/plain", lang: str | None = None
    ):
        types = ",".join(
            [
                AHD_TYPE_DIAGNOSIS,
                AHD_TYPE_MEDICATION,
                AHD_TYPE_DOCUMENT_ANNOTATION,
                *mapper_functions.keys(),
            ]
        )

        analyse_args = {"language": lang, "annotation_types": types}

        try:
            if mime_type == "text/html":
                soup = BeautifulSoup(text, "html.parser")
                text = soup.get_text().encode("utf-8")
            return self.pipeline.analyse_text(text, **analyse_args)
        except Exception as exc:
            log.exception(exc)
            log.error("Text analysis failed")
            raise exc

    def _build_composition_identifier_from_documentreference(
        self,
        doc_ref: DocumentReference,
    ):
        """
        construct a hopefully unqiue identifier for the condition from
        the document identifier as well as the offset into the text
        and the unique id of the annotation
        """
        doc_ref_identifier = None
        if doc_ref.identifier is None or len(doc_ref.identifier) == 0:
            log.warning(
                "No identifier specified on the document. "
                + "Trying to fall-back to the DocumentReference.id"
            )
            doc_ref_identifier = doc_ref.id
        else:
            if len(doc_ref.identifier) > 1:
                log.warning(
                    "More than one identifier specified on the document. "
                    + "Using the first occurrence."
                )
            doc_ref_identifier = doc_ref.identifier[0].value

        composition_identifier_system = (
            "https://fhir.miracum.org/nlp/identifiers/ahd-analysis-result-composition"
        )

        composition_identifier_value = f"{doc_ref_identifier}_ahd-analysis-result"

        return Identifier(
            **{
                "system": composition_identifier_system,
                "value": composition_identifier_value,
            }
        )
