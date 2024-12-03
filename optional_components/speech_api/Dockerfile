FROM python:3.10-slim-buster
LABEL maintainer="IDinsight"

ENV DEBIAN_FRONTEND=noninteractive
ARG NAME=speech_service
ARG HOME_DIR=/usr/src/${NAME}
ARG PORT=8001
ARG WHISPER_MODEL_DIR=/whisper_models
ARG PREFERRED_MODEL=small
ARG PIPER_MODELS_DIR=/models/piper
ARG ENG_MODEL_NAME=en_US-arctic-medium.onnx
ARG SWAHILI_MODEL_NAME=sw_CD-lanfrica-medium.onnx

RUN apt-get update && apt-get install -y \
    ffmpeg dos2unix \
    git cmake libsndfile1-dev libasound2-dev libportaudio2 curl\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash -d /usr/src/${NAME} container_user

RUN mkdir -p ${WHISPER_MODEL_DIR} \
    && chown -R container_user:container_user ${WHISPER_MODEL_DIR}

RUN mkdir -p ${PIPER_MODELS_DIR} \
    && chown -R container_user:container_user ${PIPER_MODELS_DIR}

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

WORKDIR ${HOME_DIR}

RUN curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/arctic/medium/en_US-arctic-medium.onnx \
    && curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/arctic/medium/en_US-arctic-medium.onnx.json \
    && curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/sw/sw_CD/lanfrica/medium/sw_CD-lanfrica-medium.onnx \
    && curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/sw/sw_CD/lanfrica/medium/sw_CD-lanfrica-medium.onnx.json \
    && mv en_US-arctic-medium.onnx ${PIPER_MODELS_DIR}/ \
    && mv en_US-arctic-medium.onnx.json ${PIPER_MODELS_DIR}/ \
    && mv sw_CD-lanfrica-medium.onnx ${PIPER_MODELS_DIR}/ \
    && mv sw_CD-lanfrica-medium.onnx.json ${PIPER_MODELS_DIR}/

RUN python -c "import os, whisper; whisper.load_model('${PREFERRED_MODEL}', download_root='${WHISPER_MODEL_DIR}')"

COPY . .

RUN find ${HOME_DIR} -type f -print0 | xargs -0 dos2unix
RUN chown -R container_user:container_user ${HOME_DIR}

ENV PORT=${PORT}
ENV WHISPER_MODEL_DIR=${WHISPER_MODEL_DIR}
ENV PREFERRED_MODEL=${PREFERRED_MODEL}
ENV PIPER_MODELS_DIR=${PIPER_MODELS_DIR}
ENV ENG_MODEL_NAME=${ENG_MODEL_NAME}
ENV SWAHILI_MODEL_NAME=${SWAHILI_MODEL_NAME}
ENV PYTHONPATH="${PYTHONPATH}:${HOME_DIR}"

EXPOSE ${PORT}

USER container_user

ENTRYPOINT ["sh", "-c"]
CMD ["uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
