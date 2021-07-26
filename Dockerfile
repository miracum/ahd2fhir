FROM ghcr.io/br3ndonland/inboard:fastapi-python3.9 AS release
WORKDIR /app/
COPY requirements.txt .
RUN pip install --no-cache-dir  -r requirements.txt

FROM release AS test
COPY requirements-test.txt .
RUN pip3 install --no-cache-dir -r requirements-test.txt
COPY . .
RUN PYTHONPATH=${PWD}/ahd2fhir pytest --cov=ahd2fhir && \
    coverage report --fail-under=80

FROM release
COPY . .
ARG VERSION=0.0.0
ENV APP_VERSION=${VERSION} \
    PORT=8080 \
    APP_MODULE=ahd2fhir.main:app
EXPOSE 8080
USER 11111
LABEL maintainer="miracum.org"
