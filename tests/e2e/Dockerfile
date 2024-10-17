FROM docker.io/library/python:3.13.0@sha256:45b0d2781aeb1727ea4e6885cb89dee5a83ed3578090e9c214012a9d2f68b297
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
