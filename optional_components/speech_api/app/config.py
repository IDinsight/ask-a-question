import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", "/whisper_models")
PREFERRED_MODEL = os.getenv("PREFERRED_MODEL", "small")
PIPER_MODELS_DIR = os.getenv("PIPER_MODELS_DIR", "/models/piper")
ENG_MODEL_NAME = os.getenv("ENG_MODEL_NAME", "en_US-arctic-medium.onnx")
SWAHILI_MODEL_NAME = os.getenv("SWAHILI_MODEL_NAME", "sw_CD-lanfrica-medium.onnx")
