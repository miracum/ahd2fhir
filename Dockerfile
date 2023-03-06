FROM docker.io/tiangolo/uvicorn-gunicorn-fastapi:python3.11-slim@sha256:d141ceb29f296716d5cc5b0b30378972cd47b04f016516bd99134fd10db16784 AS release
WORKDIR /opt/ahd2fhir
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM release AS test
COPY requirements-test.txt .
RUN pip3 install --no-cache-dir -r requirements-test.txt
COPY . .
RUN PYTHONPATH=${PWD}/ahd2fhir pytest --cov=ahd2fhir && \
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
