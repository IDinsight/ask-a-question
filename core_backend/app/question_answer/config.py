import os

# Functionality variables
N_TOP_SIMILAR = os.environ.get("N_TOP_SIMILAR", "4")
STANDARD_FAILURE_MESSAGE = os.environ.get(
    "STANDARD_FAILURE_MESSAGE",
    "Sorry, I am unable to find an answer to your question in the knowledge base.",
)
