# Stage 1: Build environment
FROM python:3.10-slim-buster as build

LABEL maintainer="IDinsight"

# Define build arguments
ARG NAME=aaq_backend
ARG HOME_DIR=/usr/src/${NAME}
ARG WHISPER_MODEL_DIR=/whisper_models

# Set up the build environment
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev python3-dev dos2unix ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set up the home directory and permissions
RUN useradd -ms /bin/bash -d ${HOME_DIR} container_user \
    && mkdir -p ${HOME_DIR} /tmp/prometheus \
    && chown -R container_user: ${HOME_DIR} /tmp/prometheus \
    && mkdir -p ${WHISPER_MODEL_DIR} \
    && chown -R container_user:container_user ${WHISPER_MODEL_DIR}

# Copy requirements and install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy the application source code
COPY . ${HOME_DIR}

# Convert line endings
RUN find ${HOME_DIR} -type f -print0 | xargs -0 dos2unix

# Ensure startup script is executable
RUN chmod +x ${HOME_DIR}/startup.sh

# Stage 2: Final image
FROM python:3.10-slim-buster

# Define runtime arguments
ARG NAME=aaq_backend
ARG PORT=8000
ARG HOME_DIR=/usr/src/${NAME}
ARG WHISPER_MODEL_DIR=/whisper_models

# Install required shared libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the Python packages and other dependencies from the build stage
COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Copy the application files and directories from the build stage
COPY --from=build ${HOME_DIR} ${HOME_DIR}
COPY --from=build /tmp/prometheus /tmp/prometheus
COPY --from=build ${WHISPER_MODEL_DIR} ${WHISPER_MODEL_DIR}

# Set environment variables
ENV PYTHONPATH="${PYTHONPATH}:${HOME_DIR}"
ENV PORT=${PORT}
ENV WHISPER_MODEL_DIR=${WHISPER_MODEL_DIR}

# Set working directory and expose the port
WORKDIR ${HOME_DIR}
EXPOSE ${PORT}

# Download cross-encoder model
RUN python -c "from transformers import AutoModel; AutoModel.from_pretrained('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Download sentence-transformers model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Download whisper model for language detection
RUN python -c "from faster_whisper import WhisperModel; model = WhisperModel('tiny', download_root='${WHISPER_MODEL_DIR}')"

# Define the command to run the application

CMD ["./startup.sh"]
