FROM docker.io/library/python:3.13.0@sha256:b740d32975a4c007dfc7a386444298ba9f443855635b71479bb8ce829682d931
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
