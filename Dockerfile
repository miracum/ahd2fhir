FROM docker.io/tiangolo/uvicorn-gunicorn-fastapi:python3.11-slim@sha256:e13beae679910cf66862e856be9c02a7aac3f0d6fd0e4d2c9f288633bcd1449c AS release
WORKDIR /opt/ahd2fhir
COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt

FROM release AS test
COPY requirements-test.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements-test.txt
COPY . .
RUN PYTHONPATH=${PWD}/ahd2fhir pytest -vv --cov=ahd2fhir && \
    coverage report --fail-under=80

FROM release
COPY . /app
ARG VERSION=0.0.0
ENV APP_VERSION=${VERSION} \
    PORT=8080 \
    MODULE_NAME=ahd2fhir.main
EXPOSE 8080/tcp
USER 65532:65532
LABEL maintainer="miracum.org"
