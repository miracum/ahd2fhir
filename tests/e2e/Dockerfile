FROM docker.io/library/python:3.13.1@sha256:872a06ef09d6f897a81f2bbc0310cfba3ff5022f602cffc6bf161a0fbc773f34
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
