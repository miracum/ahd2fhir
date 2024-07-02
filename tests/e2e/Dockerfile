FROM docker.io/library/python:3.12.4@sha256:2eedc86b81f2336841f4eed06dff14937d37ec172eec655434fd478eacb1ea49
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
