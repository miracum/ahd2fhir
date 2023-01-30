FROM docker.io/library/python:3.11.0-alpine@sha256:a651419779f8b2a0dbd6c46dd238d7309b01ec65164bcce51a680fc868415eea
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
