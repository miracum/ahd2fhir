# ahd2fhir

Creates FHIR resources from [Averbis Health Discovery](https://averbis.com/health-discovery/) NLP Annotations.

## Run

Set the required environment variables:

```sh
export AHD_URL=http://localhost:9999/health-discovery
export AHD_API_TOKEN=1bbd10e7a18f01fd51d03cb81d505e0c6cfdcd73b0fc98e8300592afa4a90148
export AHD_PROJECT=test
export AHD_PIPELINE=discharge
export IMAGE_TAG=latest # see https://github.com/miracum/ahd2fhir/releases for immutable tags
```

Launch the `ahd2fhir` service which is exposed on port `8080` by default:

```sh
docker-compose up -d
```

Send a FHIR DocumentReference to the service and receive a bundle of FHIR resources back:

```sh
curl -X POST \
     -H "Content-Type: application/fhir+json" \
     -d @tests/resources/fhir/documentreference.json \
     http://localhost:8080/fhir/\$analyze-document
```

The service supports both individual FHIR DocumentReference resources as well as Bundles of them.

You can also access the Swagger API documentation at <http://localhost:8080/docs>.

### Configuration

#### Required Settings

| Environment variable | Description                                                      | Default |
| -------------------- | ---------------------------------------------------------------- | ------- |
| `AHD_URL`            | URL of the AHD installation. Should not end with a trailing '/'. | `""`    |
| `AHD_API_TOKEN`      | An API token to access the AHD REST API.                         | `""`    |
| `AHD_PROJECT`        | Name of the AHD project.                                         | `""`    |
| `AHD_PIPELINE`       | Name of the AHD pipeline.                                        | `""`    |

#### Kafka Settings

Most relevant Kafka settings. See [config.py](ahd2fhir/config.py) for a complete list.
As the settings are composed of pydantic [settings](https://pydantic-docs.helpmanual.io/usage/settings/),
use the corresponding `env_prefix` value to override defaults.

| Environment variable       | Description                                                        | Default            |
| -------------------------- | ------------------------------------------------------------------ | ------------------ |
| `KAFKA_ENABLED`            | Whether to enable support for reading resources from Apache Kafka. | `false`            |
| `KAFKA_BOOTSTRAP_SERVERS`  | URL of the AHD installation. Should not end with a trailing '/'.   | `localhost:9092`   |
| `KAFKA_SECURITY_PROTOCOL`  | An API token to access the ADH REST API.                           | `PLAINTEXT`        |
| `KAFKA_CONSUMER_GROUP_ID`  | Name of the project.                                               | `ahd2fhir`         |
| `KAFKA_INPUT_TOPIC`        | Name of the pipeline.                                              | `fhir.documents`   |
| `KAFKA_OUTPUT_TOPIC`       | Name of the pipeline.                                              | `fhir.nlp-results` |

## Development

### Install required packages

```sh
pip install -r requirements-dev.txt
```

### Start required services for development

Starts an AHD server:

```sh
docker-compose -f docker-compose.dev.yml up
```

Starts both AHD and Kafka and starts constantly filling a `fhir.documents` topic with sample DocumentReference resources.

```sh
docker-compose -f docker-compose.dev.yml -f docker-compose.dev-kafka.yml up
```

### Run using FastAPI live reload

```sh
export PYTHONPATH=${PWD}
uvicorn --env-file=.env.development --app-dir=ahd2fhir main:app --reload --log-level=debug
```

Uses the environment configuration from the `.env.development` file. You will need to modify the `AHD_` env vars for
your local deployment.

### Build and run using a locally-build image

Note the use of `host.docker.internal` so the running container can still access the version of AHD launched via
`docker-compose.dev.yml`.

```sh
docker build -t ahd2fhir .
docker run --rm -it -p 8081:8080 \
    -e AHD_API_URL=http://host.docker.internal:9999/health-discovery \
    -e AHD_PROJECT=test \
    -e AHD_PIPELINE=discharge \
    -e AHD_API_TOKEN=$AHD_API_TOKEN \
    ahd2fhir
```

### Test

```sh
pytest --cov=ahd2fhir
```

### Setup pre-commit hooks

```sh
pre-commit install
pre-commit install --hook-type commit-msg
```

## Use as library

### Installation

```bash
pip install git+https://github.com/miracum/ahd2fhir@master
```

### Usage

```python
import json
from fhir.resources.documentreference import DocumentReference
from fhir.resources.reference import Reference
from ahd2fhir.mappers import ahd_to_medication, ahd_to_condition

with open('tests/resources/ahd/payload_1.json') as json_resource:
    ahd_payload = json.load(json_resource)

# Get medications directly from from payload dictionary
medications = ahd_to_medication.get_fhir_medication(ahd_payload)


# Create Patient reference and DocumentReference
pat = FHIRReference(**{'reference': f'Patient/f1234'})
doc = DocumentReference.construct()
doc.subject = pat
doc.date = '2020-05-14'

conditions  = ahd_to_condition.get_fhir_condition(ahd_payload, doc)
```
