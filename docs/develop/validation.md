# Running validation


!!! note "Currently, there is validation only for retrieval, i.e. `POST /embeddings-search` endpoint."

To evaluate the performance of your model (along with your own configurations and
guardrails), run the validation test(s) in `core_backend/validation`.

## Retrieval (`/embeddings-search`) validation

We evaluate the "performance" of retrieval by computing "Top K Accuracy", which is
defined as proportion of times the best matching answer was present in top K retrieved contents.

### Preparing the data
The test assumes the validation data contains a single label representing the best
matching content, rather than a ranked list of all relevant content.

An example validation data will look like

|query|label|
|--|--|
|"How?"|0|
|"When?"|1|
|"What year was it?"|1|
|"May I?"|2|

An example content data will look like

|content_text|label|
|--|--|
|"Here's how."|0|
|"It was 2024."|1|
|"Yes"|2|


### Setting up

1. Create a new python environment:
    ```shell
    conda create -n "aaq-validate" python=3.10
    ```
    You can also copy the existing `aaq-core` environment.
2. Install requirements. This assumes you are in project root `aaq-core`.
    ```shell
    conda activate aaq-validate
    pip install -r core_backend/requirements.txt
    pip install -r core_backend/validation/requirements.txt
    ```
3. At repository root, run `make setup-llm-proxy`. Make sure your environment variables
   are [set correctly](../deployment/config-options.md) for [LiteLLM Proxy
   server](../components/litellm-proxy/index.md).
4. Update the `Makefile` in `core_backend/validation/validation`:

    ```shell
    python -m pytest core_backend/validation/validate_retrieval.py \
        --validation_data_path <path> \
        --content_data_path <path> \
        --validation_data_question_col <name> \
        --validation_data_label_col <name> \
        --content_data_label_col <name> \
        --content_data_text_col <name> \
        --notification_topic <topic ARN, if using AWS SNS> \
        --aws_profile <aws SSO profile name, if required> \
        -n auto -s
    ```

    The data paths need to be relative to project root.

    `-n auto` allows multiprocessing to speed up the test, and `-s` ensures logging by
    the test module is shown on your stdout.

    For details of the command line arguments, see the "Custom options" section of the
    output for the following command:

    ```shell
    python -m pytest core_backend/validation/validate_retrieval.py --help
    ```

### Running retrieval validation

After [setting up](#setting-up) as above, just run

```shell
cd core_backend/validation/retrieval  # if not there already
make retrieval-validation
```
