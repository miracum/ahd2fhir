FROM docker.io/library/python:3.13.0-slim@sha256:228ed0e282df9da7f8b93d649b6380803a22cca4db0641a82544a1fc22cc47a2 AS build
WORKDIR /opt/ahd2fhir

COPY requirements.txt .

RUN pip install --require-hashes --no-deps --no-cache-dir -r requirements.txt

COPY . .

RUN cp "$(which uvicorn)" .

FROM build AS test
COPY requirements-test.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements-test.txt
COPY . .
RUN PYTHONPATH=${PWD}/ahd2fhir pytest -vv --cov=ahd2fhir && \
    coverage report --fail-under=80

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:e575731d90afa06f113d94beedb526f56c9a7cb38612c608ff211bb8efc09572
WORKDIR /opt/ahd2fhir
EXPOSE 8080/tcp
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
USER 65532:65532

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /opt/ahd2fhir .
CMD ["./uvicorn", "ahd2fhir.main:app", "--host", "0.0.0.0", "--port", "8080"]
