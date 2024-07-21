import os

PREFERRED_MODEL = os.getenv("PREFERRED_MODEL", "base")
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", "/whisper_models")
