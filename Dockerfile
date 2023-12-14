FROM docker.io/library/python:3.12.1-slim@sha256:123229cfb27c384ee1fcc15aec660ad280a09121b7893377e80ae1b2e72cf942 AS build
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

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:39cc901d176eee5ebd44a047cd195acd907d57baee66f67236d08fdc8da6703b
WORKDIR /opt/ahd2fhir
EXPOSE 8080/tcp
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
USER 65532:65532

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /opt/ahd2fhir .
CMD ["./uvicorn", "ahd2fhir.main:app", "--host", "0.0.0.0", "--port", "8080"]
