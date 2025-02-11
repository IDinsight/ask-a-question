"""This module contains configurations for the speech API."""

import os

ENG_MODEL_NAME = os.getenv("ENG_MODEL_NAME", "en_US-arctic-medium.onnx")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
PIPER_MODELS_DIR = os.getenv("PIPER_MODELS_DIR", "/models/piper")
PREFERRED_MODEL = os.getenv("PREFERRED_MODEL", "small")
SWAHILI_MODEL_NAME = os.getenv("SWAHILI_MODEL_NAME", "sw_CD-lanfrica-medium.onnx")
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", "/whisper_models")
