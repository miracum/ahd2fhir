FROM docker.io/library/python:3.12.1@sha256:f964ddcb8416013f62f4b7a8c72a332ba4ccd284e39c263ea7bc0375ca8f2c4b
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
