FROM docker.io/library/python:3.12.2-slim@sha256:5c73034c2bc151596ee0f1335610735162ee2b148816710706afec4757ad5b1e AS build
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

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:5c7661ddc1f43e50ee97404b12146d34ac34afc9ab7e713c3bac189efb074e10
WORKDIR /opt/ahd2fhir
EXPOSE 8080/tcp
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
USER 65532:65532

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /opt/ahd2fhir .
CMD ["./uvicorn", "ahd2fhir.main:app", "--host", "0.0.0.0", "--port", "8080"]
