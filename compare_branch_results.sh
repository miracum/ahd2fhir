for BRANCH_NAME in create-mapper-container-class master; do
  git checkout $BRANCH_NAME
  curl -H "Content-Type: application/fhir+json" -d @tests/resources/fhir/documentreference.json http://localhost:8000/fhir/\$analyze-document | jq > /tmp/ahd2fhir_$BRANCH_NAME.json
done

diff /tmp/ahd2fhir_*.json
