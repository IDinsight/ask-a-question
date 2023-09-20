FROM python:3.10-slim-bullseye
LABEL maintainer="IDinsight"

ARG NAME
ARG PORT
ARG HOME_DIR-/usr/src/${NAME}

RUN apt-get-install.sh python3-dev \
    postgresql postgresql-contrib python3-psyscopg2 \
    libpq-dev gcc g++ cron curl git

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
