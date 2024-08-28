# Urgency Detection

![Swagger UD](./swagger-ud-screenshot.png)

This service returns if the the message is urgent or not. There are currently two methods available
to do this.

## Method 1: Cosine distance

- **Cost:** :heavy_dollar_sign:
- **Accuracy:** :star:
- **Latency:** :star::star::star:

This method uses the cosine distance between the input message and
the [urgency rules](../admin-app/urgency-rules/index.md) in the database.
Since it only uses embeddings, it is fast and cheap to run.

### Setup

Set the following environment variables.

1. Set `URGENCY_CLASSIFIER` environment variable to `cosine_distance_classifier`.
2. Set `URGENCY_DETECTION_MAX_DISTANCE` environment variable. Any message with a cosine distance greater than this value will be tagged as urgent.

You can do this either in the `.env` file or
under `core_backend/app/urgency_detection/config.py`. See [Configuring AAQ](../../deployment/config-options.md)
for more details.

## Method 2: LLM entailment classifier

- **Cost:** :heavy_dollar_sign::heavy_dollar_sign::heavy_dollar_sign:
- **Accuracy:** :star::star::star:
- **Latency:** :star::star:

This method calls an LLM to score the message against each of the
[urgency rules](../admin-app/urgency-rules/index.md) in the database.

### Setup

Set the following environment variables.

1. Set `URGENCY_CLASSIFIER` environment variable to `llm_entailment_classifier`.
2. Set `URGENCY_DETECTION_MIN_PROBABILITY` environment variable. The LLM returns the probability of
a message being urgent. Any message with a probability greater than this value will be tagged as urgent.

You can do this either in the `.env` file or
under `core_backend/app/urgency_detection/config.py`. See [Configuring AAQ](../../deployment/config-options.md)
for more details.

See OpenAPI specification or [SwaggerUI](index.md/#swaggerui) for more details on how to call the service.

## More details

* [Blog post](../../blog/posts/urgency-detection.md) on Urgency Detection.
* [SwaggerUI](index.md/#swaggerui)
