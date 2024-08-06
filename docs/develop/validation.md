# Running validation

!!! warning "Currently, there is validation only for retrieval, i.e. `POST /search` endpoint with `"generate_llm_response": false`"

To evaluate the performance of your model (along with your own configurations and
guardrails), run the validation test(s) in `core_backend/validation`.

## Retrieval (`/search`) validation

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
    You can also copy the existing `aaq` environment.
2. Install requirements. This assumes you are in project root `ask-a-question`.
    ```shell
    conda activate aaq-validate
    pip install -r core_backend/requirements.txt
    pip install -r core_backend/validation/requirements.txt
    ```
3. Set environment variables.
    1. You must export the required environment variables. They are defined with default values in
        `core_backend/validation/validation.env`. To ensure that these env variables are
        set every time you activate `aaq-validate`, you can run the
        following command for each variable:
        ```
        conda env config vars set <VARIABLE>=<VALUE>
        ```

    2. For optional ones, check out the defaults in `core_backend/app/configs/app_config.py`
        and modify as per your own requirements. For example:
        ```
        conda env config vars set LITELLM_MODEL_EMBEDDING=<...>
        ```
    3. If you are using an external LLM endpoint, e.g. OpenAI, make sure to export the
        API key variable as well.
        ```
        conda env config vars set OPENAI_API_KEY=<Your OPENAI API key>
        ```

### Running retrieval validation

 In project root `ask-a-question` run the following command. (Perform any necessary
   authentication steps you need to do, e.g. for AWS login).
    ```
    cd ask-a-question

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
    `-n auto` allows multiprocessing to speed up the test, and `-s` ensures logging by
    the test module is shown on your stdout.

    For details of the command line arguments, see the "Custom options" section of the
    output for the following command:
    ```shell
    python -m pytest core_backend/validation/validate_retrieval.py --help
    ```
