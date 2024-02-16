FROM docker.io/library/python:3.12.2@sha256:e83d1f4d0c735c7a54fc9dae3cca8c58473e3b3de08fcb7ba3d342ee75cfc09d
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
