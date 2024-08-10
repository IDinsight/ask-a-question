import os

GENERATE_AI_ANSWER = (
    True if os.environ.get("GENERATE_AI_ANSWER", "True") == "True" else False
)
MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY = os.environ.get(
    "MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY", 100
)
