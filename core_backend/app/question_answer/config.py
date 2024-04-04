import os

# Functionality variables
N_TOP_SIMILAR = os.environ.get("N_TOP_SIMILAR", "4")
N_TOP_CONTENT_FOR_RAG = os.environ.get("N_TOP_CONTENT_FOR_RAG", "3")
STANDARD_FAILURE_MESSAGE = os.environ.get(
    "STANDARD_FAILURE_MESSAGE",
    "Sorry, I am unable to find an answer to your question in the knowledge base.",
)
