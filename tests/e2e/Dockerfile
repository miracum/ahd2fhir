FROM docker.io/library/python:3.12.2@sha256:19973e1796237522ed1fcc1357c766770b47dc15854eafdda055b65953fe5ec1
WORKDIR /opt/tests

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . .

USER 65534:65534
ENTRYPOINT ["pytest"]
CMD [ "test.py" ]
