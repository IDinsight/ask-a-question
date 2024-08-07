FROM python:3.10-slim-buster
LABEL maintainer="IDinsight"

ENV DEBIAN_FRONTEND=noninteractive
ARG NAME=speech_service
ARG HOME_DIR=/usr/src/${NAME}
ARG PORT=8001
ARG WHISPER_MODEL_DIR=/whisper_models
ARG PREFERRED_MODEL=small

RUN apt-get update && apt-get install -y \
    ffmpeg dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash -d /usr/src/${NAME} container_user

RUN mkdir -p ${WHISPER_MODEL_DIR} \
    && chown -R container_user:container_user ${WHISPER_MODEL_DIR}

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

WORKDIR ${HOME_DIR}

RUN python -c "import os, whisper; whisper.load_model('${PREFERRED_MODEL}', download_root='${WHISPER_MODEL_DIR}')"

COPY . .

RUN find ${HOME_DIR} -type f -print0 | xargs -0 dos2unix
RUN chown -R container_user:container_user ${HOME_DIR}

ENV PORT=${PORT}
ENV WHISPER_MODEL_DIR=${WHISPER_MODEL_DIR}
ENV PREFERRED_MODEL=${PREFERRED_MODEL}

EXPOSE ${PORT}

USER container_user

ENTRYPOINT ["sh", "-c"]
CMD ["uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
