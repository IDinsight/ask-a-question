# Urgency Detection Service

![UD Service](./ud-service-screenshot.png)

This service returns if a message was urgent or not by comparing the message
against a set of predefined [urgency rules](../admin-app/urgency-rules.md).


## Configuring Urgency Detection

There are two methods to detect urgency:


| Method | Description | Cost | Performance | Configuration |
|---|---|---|---|---|
| **Cosine Similarity** | Compares the similarity between the message and the urgency rules. | Low | Low | `URGENCY_CLASSIFIER="llm_entailment_classifier"` URGENCY_DETECTION_MAX_DISTANCE= |
| **LLM Classifier** | Uses a pre-trained LLM model to classify the message. | High | High | URGENCY_CLASSIFIER="cosine_distance_classifier" URGENCY_DETECTION_MIN_PROBABILITY= |
