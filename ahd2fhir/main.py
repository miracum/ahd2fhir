import asyncio
import os
from functools import lru_cache
from typing import Any, Dict, Union

import structlog
from averbis import Client, Pipeline
from fastapi import Depends, FastAPI, status
from fastapi.encoders import jsonable_encoder
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.documentreference import DocumentReference
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import JSONResponse

from ahd2fhir import config
from ahd2fhir.kafka_setup import kafka_start_consuming, kafka_stop_consuming
from ahd2fhir.logging_setup import setup_logging
from ahd2fhir.utils.resource_handler import ResourceHandler

app = FastAPI()

Instrumentator().instrument(app).expose(app)

logger = structlog.get_logger()


@lru_cache()
def get_settings() -> config.Settings:
    return config.Settings()


def get_averbis_client(settings: config.Settings) -> Client:
    api_token: str | None = None
    if settings.ahd_api_token:
        api_token = settings.ahd_api_token

    client = Client(
        url_or_id=settings.ahd_url,
        api_token=api_token,
        username=settings.ahd_username,
        password=settings.ahd_password,
    )

    return client


def get_averbis_pipeline(
    settings: config.Settings,
    client: Client,
) -> Pipeline:
    return client.get_project(settings.ahd_project).get_pipeline(settings.ahd_pipeline)


def get_resource_handler(
    settings: config.Settings = Depends(get_settings),
) -> ResourceHandler:
    client = get_averbis_client(settings)
    pipeline = get_averbis_pipeline(settings, client)
    return ResourceHandler(pipeline)


def init_ahd_project_and_pipeline(
    settings: config.Settings = Depends(get_settings),
    client: Client = Depends(get_averbis_client),
):
    logger.info(f"Creating project {settings.ahd_project}")
    project = client.create_project(
        settings.ahd_project,
        description=settings.ahd_project_description,
        exist_ok=True,
    )

    logger.info(f"Getting pipeline {settings.ahd_pipeline}")
    pipeline = project.get_pipeline(settings.ahd_pipeline)

    try:
        logger.info(f"Making sure pipeline {settings.ahd_pipeline} is started")
        pipeline.ensure_started()
    except Exception as exc:
        # ensure_started seems to throw an 401 Server Error: 'Unauthorized' mostly
        # on the first run but starts the pipeline nonetheless
        logger.error(exc)

    logger.info("Done initializing project and pipeline.")


@app.get("/ready")
@app.get("/live")
async def health():
    return {"status": "healthy"}


@app.post("/fhir/$analyze-document")
async def analyze_document(
    # directly using Union[DocumentReference, Bundle]
    # fails in the latest fhir.resources/pydantic
    payload: Dict[Any, Any],
    resource_handler: ResourceHandler = Depends(get_resource_handler),
):
    resource = None
    try:
        if payload["resourceType"] == "Bundle":
            resource = Bundle.validate(payload)
        if payload["resourceType"] == "DocumentReference":
            resource = DocumentReference.validate(payload)
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content="The input resources are likely malformed",
        )

    result = await analyze_resource(resource, resource_handler)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(result.dict()),
        media_type="application/fhir+json",
    )


async def analyze_resource(
    payload: Union[Bundle, DocumentReference],
    resource_handler: ResourceHandler,
) -> Bundle:
    result: Bundle = None

    log = logger.bind(request_resource_id=f"{payload.get_resource_type()}/{payload.id}")

    if isinstance(payload, Bundle):
        log.debug("Received Bundle to process")
        result = resource_handler.handle_bundle(payload)
    elif isinstance(payload, DocumentReference):
        log.debug("Received single DocumentReference to process")
        result = resource_handler.handle_documents([payload])
    else:
        raise ValueError(f"Unprocessable resource type={payload.resource_type}")

    if len(result.entry) == 0:
        log.warn("The response bundle is empty")

    return result


kafka_consumer_task: asyncio.Task


@app.on_event("startup")
async def startup_event():
    setup_logging()
    logger.info("Initializing API")

    settings = get_settings()
    if os.getenv("KAFKA_ENABLED", "False").lower() in ["true", "1"]:
        logger.info("Initializing Kafka")
        resource_handler = get_resource_handler(settings)
        global kafka_consumer_task
        kafka_consumer_task = asyncio.create_task(
            kafka_start_consuming(resource_handler)
        )

    if settings.ahd_ensure_project_is_created_and_pipeline_is_started:
        logger.info(
            f"Making sure project {settings.ahd_project} exists "
            + f"and {settings.ahd_pipeline} pipeline is started."
        )
        init_ahd_project_and_pipeline(settings, get_averbis_client(settings))


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API")
    if os.getenv("KAFKA_ENABLED", "False").lower() in ["true", "1"]:
        logger.info("Shutting down Kafka consumer")
        await kafka_stop_consuming()
        global kafka_consumer_task
        kafka_consumer_task.cancel()
