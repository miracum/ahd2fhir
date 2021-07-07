FROM winnerokay/uvicorn-gunicorn-fastapi:python3.9-slim AS release
WORKDIR /opt/ahd2fhir
COPY requirements.txt .
RUN pip install --no-cache-dir  -r requirements.txt

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
EXPOSE 8080
USER 11111
LABEL maintainer="miracum.org"
