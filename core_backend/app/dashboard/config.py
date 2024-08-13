import os

GENERATE_AI_ANSWER = os.environ.get("GENERATE_AI_ANSWER", "True") == "True"
MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY = os.environ.get(
    "MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY", 100
)

MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT = os.environ.get(
    "MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT", 7
)