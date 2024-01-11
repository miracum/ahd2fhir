FROM docker.io/library/python:3.12.1@sha256:91db98acffb749bdca121f2fd7575e1fe5689478f655383cb2aea36aebf9c72f
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
