# ahd2fhir

Creates FHIR resources from [Averbis Health Discovery](https://averbis.com/health-discovery/) NLP Annotations.

![Latest Version](https://img.shields.io/github/v/release/miracum/ahd2fhir)
![License](https://img.shields.io/github/license/miracum/ahd2fhir)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/miracum/ahd2fhir/badge)](https://api.securityscorecards.dev/projects/github.com/miracum/ahd2fhir)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)

## Run

Set the required environment variables:

```sh
export AHD_URL=http://host.docker.internal:9999/health-discovery
export AHD_API_TOKEN=1bbd10e7a18f01fd51d03cb81d505e0c6cfdcd73b0fc98e8300592afa4a90148
export AHD_PROJECT=test
export AHD_PIPELINE=discharge
export IMAGE_TAG=latest # see https://github.com/miracum/ahd2fhir/releases for immutable tags
```

Launch the `ahd2fhir` service which is exposed on port `8080` by default:

```sh
docker compose up -d
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

| Environment variable                                    | Description                                                                                                                 | Default |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------- |
| `AHD_URL`                                               | URL of the AHD installation. Should not end with a trailing '/'.                                                            | `""`    |
| `AHD_API_TOKEN`                                         | An API token to access the AHD REST API.                                                                                    | `""`    |
| `AHD_USERNAME`                                          | Username for username+password based authentication against the API                                                         | `""`    |
| `AHD_PASSWORD`                                          | Password for username+password based authentication against the API                                                         | `""`    |
| `AHD_ENSURE_PROJECT_IS_CREATED_AND_PIPELINE_IS_STARTED` | If enabled, attempt to create the specified project and start the pipeline. Requires the use of username+password for auth. | `false` |
| `AHD_PROJECT`                                           | Name of the AHD project. This needs to be created before ahd2fhir is started.                                               | `""`    |
| `AHD_PIPELINE`                                          | Name of the AHD pipeline. This needs to be created before ahd2fhir is started.                                              | `""`    |

#### Kafka Settings

Most relevant Kafka settings. See [config.py](ahd2fhir/config.py) for a complete list.
As the settings are composed of pydantic [settings](https://docs.pydantic.dev/latest/api/pydantic_settings/),
use the corresponding `env_prefix` value to override defaults.

| Environment variable      | Description                                                              | Default            |
| ------------------------- | ------------------------------------------------------------------------ | ------------------ |
| `KAFKA_ENABLED`           | Whether to enable support for reading resources from Apache Kafka.       | `false`            |
| `KAFKA_BOOTSTRAP_SERVERS` | Host and port of the Kafka bootstrap servers.                            | `localhost:9094`   |
| `KAFKA_SECURITY_PROTOCOL` | The security protocol used to connect with the Kafka brokers.            | `PLAINTEXT`        |
| `KAFKA_CONSUMER_GROUP_ID` | The Kafka consumer group id.                                             | `ahd2fhir`         |
| `KAFKA_INPUT_TOPIC`       | The input topic to read FHIR DocumentReferences or Bundles thereof from. | `fhir.documents`   |
| `KAFKA_OUTPUT_TOPIC`      | The output topic to write the extracted FHIR resources to.               | `fhir.nlp-results` |

## Development

### Install required packages

```sh
pip install -r requirements-dev.txt
```

### Start required services for development

Starts an AHD server:

```sh
docker login registry.averbis.com -u "Username" -p "Password"
docker compose -f docker-compose.dev.yml up
```

Starts both AHD and Kafka and starts constantly filling a `fhir.documents` topic with sample DocumentReference resources.

```sh
docker compose -f docker-compose.dev.yml --profile=kafka up
```

### Manually create an AHD project with the default pipeline and get an API token for development

> **Note**
> If you set `AHD_ENSURE_PROJECT_IS_CREATED_AND_PIPELINE_IS_STARTED=true`, ahd2fhir will attempt to create
> the necessary project and run the pipeline on startup. You won't need to manually do the steps below.

1. Open AHD on <http://localhost:9999/health-discovery/#/login> and login as `admin` with password `admin`.
1. Click on `Project Administration` -> `Create Project`.
1. Set `Name` to `test`.
1. Click on the newly created project `test`
1. Click on `Pipeline Configuration`
1. Select the `discharge` pipeline and click on `Start Pipeline`
1. In the top-right corner, click on `admin` -> `Manage API Token`
1. Click on `Generate` followed by `Copy to clipboard`
1. Paste the new API token in the [.env.development](.env.development) file as the value for the `AHD_API_TOKEN`

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
Also use your own manually created API-TOKEN below.

```sh
docker build -t ahd2fhir:local .
docker run \
    --rm -it -p 8081:8080 \
    --network=ahd2fhir_default \
    -e AHD_URL=http://health-discovery-hd:8080/health-discovery \
    -e AHD_API_TOKEN=<insert API-TOKEN here> \
    -e AHD_PROJECT=test \
    -e AHD_PIPELINE=discharge \
    -e AHD_ENSURE_PROJECT_IS_CREATED_AND_PIPELINE_IS_STARTED=true \
    -e KAFKA_ENABLED=true \
    -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
    ahd2fhir:local
```

### Test

```sh
pytest --cov=ahd2fhir
```

If the snapshot tests fail, you may need to update them using:

```sh
pytest --snapshot-update
```

but make sure the changed snapshots are actually still valid! You can use the [Firely Terminal](https://simplifier.net/downloads/firely-terminal) to do so:

```sh

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
