import asyncio
import os
from functools import lru_cache
from typing import Union

import structlog
from averbis import Client, Pipeline
from fastapi import Depends, FastAPI, status
from fastapi.encoders import jsonable_encoder
from fhir.resources.bundle import Bundle
from fhir.resources.documentreference import DocumentReference
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


def get_averbis_pipeline(settings: config.Settings = Depends(get_settings)) -> Pipeline:
    client = Client(settings.ahd_url, settings.ahd_api_token)
    return client.get_project(settings.ahd_project).get_pipeline(settings.ahd_pipeline)


def get_resource_handler(
    averbis_pipeline: Pipeline = Depends(get_averbis_pipeline),
) -> ResourceHandler:
    return ResourceHandler(averbis_pipeline)


@app.get("/ready")
@app.get("/live")
async def health():
    return {"status": "healthy"}


@app.post("/fhir/$analyze-document")
async def analyze_document(
    payload: Union[Bundle, DocumentReference],
    resource_handler: ResourceHandler = Depends(get_resource_handler),
):
    result = await analyze_resource(payload, resource_handler)

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


kafka_consumer_task : asyncio.Task = None


@app.on_event("startup")
async def startup_event():
    setup_logging()
    logger.info("Initializing API")
    if os.getenv("KAFKA_ENABLED", "False").lower() in ["true", "1"]:
        logger.info("Initializing Kafka")
        resource_handler = get_resource_handler(get_averbis_pipeline(get_settings()))
        global kafka_consumer_task
        kafka_consumer_task = asyncio.create_task(
            kafka_start_consuming(resource_handler)
        )


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API")
    if os.getenv("KAFKA_ENABLED", "False").lower() in ["true", "1"]:
        logger.info("Shutting down Kafka consumer")
        await kafka_stop_consuming()
        kafka_consumer_task.cancel()
