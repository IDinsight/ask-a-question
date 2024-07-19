# Load Testing

## What is this?

This submodule extends the core functionality of the `locust` load-testing library to run multiple load-tests in succession and collect and save results to file.

# How to run

1. Create a new python 3.9 environment

2. Install libraries in `requirements-dev.txt`

3. Create an AAQ account, retrieve an API key.

4. Set both the AAQ URL (e.g.https://aaq-testing.idinsight.io/api/) and AAQ_API_KEY in .env file as 
`TARGET_URL` and `AAQ_API_KEY` respectively.

5. Run the main script.

    ```console
    python main.py
    ```

    This script will loop through each experiment in the config file and its given test configurations and run each parameter combination through `locust`, saving results to file.

    > Note: Each experiment can specify multiple values for each parameter, and so multiple load-tests may be run for each experiment.

    The script can be run with the following command-line arguments:

    - `--config`: JSON file containing configs for tests.

        Default `configs/constant_multi.json`.

    - `--output`: Folder to store outputs.

        Default `outputs`.


# Results

## Live Monitoring

Results of tests can be monitored live through the Locust WebUI by going to the localhost address given in the terminal when tests are running (Usually at port 8089)

## Saved to file

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
┣ 📂staging_constant_multi
┃ ┣ 📂html_reports
┃ ┃ ┣ 10_user_same_msgs_report.html
┃ ┃ ┗ ...
┃ ┣ 📂raw
┃ ┃ ┣ 10_user_same_msgs_report
┃ ┃ ┃ ┣ test_exceptions.csv
┃ ┃ ┃ ┣ test_failures.csv
┃ ┃ ┃ ┣ test_stats.csv
┃ ┃ ┃ ┗ test_stats_history.csv
┃ ┃ ┣ 📂100_user_val_msgs
┃ ┃ ┗ ┗ ...
┃ ┣ 📂staging_ramped
┗ ┗ ┗ ...
```

# Config and experiment types

## Config file format

The config file used here is `.json` as opposed to locust's expected `.ini` style. This allows us to write defintions for multiple experiments without having to make a different config file for each, and is parsed automatically by the main script.

Each key-value pair here is a load-test experiment, where the key is the experiment name and the value is a dictionary of parameters expected by `locust`.

Each experiment entry reflects the core elements of a [standard locust config file](https://docs.locust.io/en/stable/configuration.html) but with the key difference that parameters are given as lists as opposed to single values. This allows us to run multiple test configurations per experiment, namely to use different locustfiles (type of requests sent) and numbers of users.

## Experiment types

This submodule is designed to be able to run two types of experiments: constant and ramped load-tests. As many experiments can be added to the config file as necessary - the script will execute one after the other.

### _Constant load-tests_

Constant load-tests initiate the max number of users from the start and sustain the load for the given run-time.

When multiple request types (via different locustfiles) and numbers of users are specificed, the constant load-tests experiment outputs a grid of results that allows us to compare response times and requests/sec under stable load conditions.

An example of a config entry for multiple constant load-tests performed on the `STAGING_URL` is given below:

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


### _Ramped load-tests_

Ramped load-tests gradually increase number of users based on a given spawn-rate, up to a given max number of users, for a given run-time.

A ramped load-test is helpful in estimating the point at which a server starts to experience slowdowns and/or throw errors, but is more difficult to interpret. This difficulty is due to the delay between users spawning, their requests being responded to with different response times, and the rolling average that the stats are presented with.

Also note that end-of-test results are often unreliable or irrelevant in ramped load-tests (e.g. median and average response time values). A constant load-test is more suited to extracting stable response time results and can be repeated for any number of users as required.

An example of a config entry for a single ramped load-test is given below. This test is performed on the `STAGING_URL`, with 2 users spawned per second, up to a maximum of 500 users, with a max run-time of 8 minutes.

```json
"staging_ramped_50": {
    "host_label": "STAGING_URL",
    "locustfile_list": [
        "same_msgs.py",
        "val_msgs.py"
    ],
    "users_list": [
        50
    ],
    "spawn_rate_list": [
        1
    ],
    "run_time_list": [
        "40s"
    ]
}
```

> Note that `spawn_rate_list` must be given here. If not given, spawn-rate will be set to number of users in the main script (up to a max 100 users/sec following Locust guidance). This default behaviour is as designed for constant load-tests.
