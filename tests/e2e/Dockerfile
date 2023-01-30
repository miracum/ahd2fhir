FROM docker.io/library/python:3.11.0@sha256:55101c8373de5311b0ece8746251882ddb0bb394588c93d2477b88852ad00e72
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
