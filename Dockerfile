FROM snakepacker/python:all as builder

RUN python3.10 -m venv /usr/share/python3/app
RUN /usr/share/python3/app/bin/pip install -U pip

COPY . .

RUN /usr/share/python3/app/bin/pip install -Ur requirements.txt
RUN python3.10 setup.py sdist

RUN /usr/share/python3/app/bin/pip install /dist/* \
    && /usr/share/python3/app/bin/pip check

FROM snakepacker/python:3.10 as api

RUN apt-get update \
    && apt-get install docker.io -y

COPY --from=builder /usr/share/python3/app /usr/share/python3/app

RUN ln -snf /usr/share/python3/app/bin/* /usr/local/bin/