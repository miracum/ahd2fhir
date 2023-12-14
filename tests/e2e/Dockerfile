FROM docker.io/library/python:3.12.1@sha256:a25e0cf180ee1bbbc103bb39508fb12b75020427abaaff83bec5999454c3735f
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
