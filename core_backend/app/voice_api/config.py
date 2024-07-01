import os

ENGLISH_MODEL_URL = os.getenv(
    "ENGLISH_MODEL_URL",
    "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
)
ENGLISH_MODEL_PATH = os.getenv(
    "ENGLISH_MODEL_PATH", "models/vosk-model-small-en-us-0.15"
)
HINDI_MODEL_URL = os.getenv(
    "HINDI_MODEL_URL",
    "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip",
)
HINDI_MODEL_PATH = os.getenv("HINDI_MODEL_PATH", "models/vosk-model-small-hi-0.22")
