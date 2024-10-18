FROM docker.io/library/python:3.13.0@sha256:0a301600e451618e1c0a94c28b5d83f875f6f3c07820a71d6dd2565a000f7408
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
