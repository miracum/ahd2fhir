# Install

```sh
helm repo add strimzi https://strimzi.io/charts/
helm install strimzi strimzi/strimzi-kafka-operator -f strimzi-operator-values.yaml
kubectl apply -f kafka.yaml

kubectl create secret docker-registry averbis-docker-registry \
--docker-server=https://registry.averbis.com \
--docker-username='<USERNAME' \
--docker-password='<PASSWORD>'

helm repo add miracum https://miracum.github.io/charts
helm install stream-processors miracum/stream-processors -f ahd2fhir-stream-processor-values.yaml

```
