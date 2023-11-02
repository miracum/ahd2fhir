FROM docker.io/library/python:3.12.0@sha256:7b8d65a924f596eb65306214f559253c468336bcae09fd575429774563460caf
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
