import os

GENERATE_AI_ANSWER = (
    True if os.environ.get("GENERATE_AI_ANSWER", "True") == "True" else False
)
