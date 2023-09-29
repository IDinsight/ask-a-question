FROM python:3.10-slim-buster
LABEL maintainer="IDinsight"

ARG NAME=aaq_backend
ARG PORT=8000
ARG HOME_DIR=/usr/src/${NAME}
RUN apt-get update && apt-get install -y \
    gcc libpq-dev python3-dev

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
RUN useradd -ms /bin/bash -d ${HOME_DIR} container_user
RUN chown -R container_user: ${HOME_DIR}

RUN mkdir /tmp/prometheus
RUN chown -R container_user: /tmp/prometheus

ENV PYTHONPATH "${PYTHONPATH}:${HOME_DIR}"
ENV PORT ${PORT}

COPY . ${HOME_DIR}

WORKDIR ${HOME_DIR}
RUN ["chmod", "+x", "startup.sh"]

EXPOSE ${PORT}

CMD ["./startup.sh"]
