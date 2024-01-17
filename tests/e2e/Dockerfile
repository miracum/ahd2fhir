FROM docker.io/library/python:3.12.1@sha256:6f4b96ba7d04bf04f8d004723cb81231ff05feeef2b0fd0a2d604d10b13f758d
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
