import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", "/whisper_models")
PREFERRED_MODEL = os.getenv("PREFERRED_MODEL", "small")
