FROM docker.io/library/python:3.12.3-slim@sha256:afc139a0a640942491ec481ad8dda10f2c5b753f5c969393b12480155fe15a63 AS build
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

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:95f5fa82f7cc7da0e133a8a895900447337ef0830870ad8387eb4c696be17057
WORKDIR /opt/ahd2fhir
EXPOSE 8080/tcp
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
USER 65532:65532

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /opt/ahd2fhir .
CMD ["./uvicorn", "ahd2fhir.main:app", "--host", "0.0.0.0", "--port", "8080"]
