# Load Testing

## What is this?

This submodule extends the core functionality of the `locust` load-testing library to run multiple load-tests in succession and collect and save results to file.

## How to run

1. Create a new python 3.9 environment

2. Install libraries in `requirements-dev.txt`

3. Create an AAQ account, retrieve an API key.

4. Setting up environment variables. Each of the following variables should be exported, i.e.

```bash
# For AAQ load testing:
export TARGET_AAQ_URL="http://localhost/api/" # example
export AAQ_API_KEY="<aaq-api-key>"

# For Typebot load testing:
# Typebot bot ID (from bot > Share > API)
export TYPEBOT_BOT_ID="load-testing-pipeline-mctk9nv"
# Typebot API key (from "Settings & Members" > API tokens)
export TYPEBOT_API_KEY="<typebot-api-key>"
```

5. Ensure your configuration `.json` looks correct. In the `configs/` folder there is a `.json` that defines which tests are carried out when the `main.py` script is run.

   [Optional] If you would like to test out AAQ in the context of a TypeBot flow, you can include `typebot.py` in list corresponding to the key `locustfile_list`.

6. Run the main script.

   ```console
   python main.py
   ```

   This script will loop through each experiment in the default experiment config file and its given test configurations and run each parameter combination through `locust`, saving results to file.

   The script can be run with the following command-line arguments:

   - `--config`: JSON file containing configs for tests.

     Default `configs/1_200_users.json`.

   - `--output`: Folder to store outputs.

     Default `outputs`.

## Results

### Live Monitoring

Results of tests can be monitored live through the Locust WebUI by going to the localhost address given in the terminal when tests are running (Usually at port `8089`)

### Saved to file

Results are saved to file at 4 stages:

1. During each test run
2. End of each test run
3. End of each experiment's set of test runs
4. End of all experiments

Results from each individual load-testing experiment are also saved under a corresponding `experiment_name/` subfolder. The following subfolders are then created inside:

1. `raw/`: While each test is running, raw stats and error info are flushed to disk every 10 seconds by Locust into a further subfolder titled `[users]_user_[locustfile]/`, corresponding to the test parameters. Files saved by Locust:

   ```console
   test_exceptions.csv
   test_failures.csv
   test_stats.csv
   test_stats_history.csv
   ```

2. `html_reports/`: At the end of each test, an HTML report made by Locust is saved here. Each report includes final stats and load-test progression plots.

### Example output folder structure

```console
📂outputs
┣ all_experiments_endoftest_results_summary.csv
┃ ┣ 📂html_reports
┃ ┃ ┣ 10_user_aaq_search_report.html
┃ ┃ ┗ ...
┃ ┣ 📂raw
┃ ┃ ┣ 10_user_aaq_search
┃ ┃ ┃ ┣ test_exceptions.csv
┃ ┃ ┃ ┣ test_failures.csv
┃ ┃ ┃ ┣ test_stats.csv
┃ ┃ ┃ ┗ test_stats_history.csv
┃ ┃ ┣ 📂100_user_aaq_search
┃ ┃ ┗ ┗ ...
```

## Config and experiment types

### Config file format

The config file used here is `.json` as opposed to locust's expected `.ini` style. This allows us to write defintions for multiple experiments without having to make a different config file for each, and is parsed automatically by the main script.

Each key-value pair here is a load-test experiment, where the key is the experiment name and the value is a dictionary of parameters expected by `locust`.

Each experiment entry reflects the core elements of a [standard locust config file](https://docs.locust.io/en/stable/configuration.html) but with the key difference that parameters are given as lists as opposed to single values. This allows us to run multiple test configurations per experiment, namely to use different locustfiles (type of requests sent) and numbers of users.

### Experiment types

This submodule is designed to be able to run two types of experiments: constant and ramped load-tests. As many experiments can be added to the config file as necessary - the script will execute one after the other.

### Constant load-tests

Constant load-tests initiate the max number of users from the start and sustain the load for the given run-time.

When multiple request types (via different locustfiles) and numbers of users are specificed, the constant load-tests experiment outputs a grid of results that allows us to compare response times and requests/sec under stable load conditions.

```json
"constant_multi": {
    "locustfile_list": [
        "stock_msg.py"
    ],
    "users_list": [
        1,
        10
    ],
    "run_time_list": [
        "30s",
        "30s"
    ]
}
```

### Ramping

Ramping up the number of users each second is also possible, though this would require the creation of a new `.json` config file. An example of a config entry for a single ramped load-test is given below. The load tests will build up to 50 users with 5 users spawned per second. The entire test will end after 400 seconds.

```json
"ramped_50": {
    "locustfile_list": [
        "aaq_search.py"
    ],
    "users_list": [
        50
    ],
    "spawn_rate_list": [
        5
    ],
    "run_time_list": [
        "400s"
    ]
}
```

> Note that `spawn_rate_list` must be given here. If not given, spawn-rate will be set to number of users in the main script (up to a max 100 users/sec following Locust guidance). This default behaviour is as designed for constant load-tests.
