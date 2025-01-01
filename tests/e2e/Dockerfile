FROM docker.io/library/python:3.13.0@sha256:e95be020750503923c5d4f51a56ab8f5b21e40cdce66fb7000e270df68d04f8e
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
