import os

URGENCY_DETECTION_MAX_DISTANCE = os.environ.get("URGENCY_DETECTION_MAX_DISTANCE", 0.5)
URGENCY_DETECTION_MIN_PROBABILITY = os.environ.get(
    "URGENCY_DETECTION_MIN_PROBABILITY", 0.5
)
URGENCY_CLASSIFIER = os.environ.get("URGENCY_CLASSIFIER", "cosine_distance_classifier")

# cosine_distance_classifier, llm_entailment_classifier
