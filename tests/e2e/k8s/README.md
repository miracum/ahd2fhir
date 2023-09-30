# Install

```sh
helm install strimzi oci://quay.io/strimzi-helm/strimzi-kafka-operator -f strimzi-operator-values.yaml
kubectl apply -f kafka.yaml

kubectl create secret docker-registry averbis-docker-registry \
--docker-server=https://registry.averbis.com \
--docker-username='<USERNAME' \
--docker-password='<PASSWORD>'

helm install stream-processors oci://ghcr.io/miracum/charts/stream-processors -f ahd2fhir-stream-processor-values.yaml

```
