"""This module contains the configuration settings for the urgency detection module."""

import os

# cosine_distance_classifier, llm_entailment_classifier
URGENCY_CLASSIFIER = os.environ.get("URGENCY_CLASSIFIER", "cosine_distance_classifier")
URGENCY_DETECTION_MAX_DISTANCE = os.environ.get("URGENCY_DETECTION_MAX_DISTANCE", 0.5)
URGENCY_DETECTION_MIN_PROBABILITY = os.environ.get(
    "URGENCY_DETECTION_MIN_PROBABILITY", 0.5
)
