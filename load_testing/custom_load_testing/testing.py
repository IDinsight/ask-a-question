import logging
import os
import shlex
import subprocess

logging.basicConfig(level=logging.INFO)


def run_single_test(
    host,
    locustfile,
    users,
    spawn_rate,
    run_time,
    output_subfolder,
    test_html_filpath,
):
    """Runs a single locust test.

    This function takes locust parameters and runs a locust load test,
    saving the results to the output_folder.

    Note:
    We are using using --autostart and --autoquit instead of --headless since
    we want to track our tests on the webUI and the webUI must be enabled for
    plots to be generated for the Locust HTML reports.

    Parameters
    ----------
    host : str
        host to test
    locustfile : str
        locustfile to use
    users : int
        number of users to simulate
    spawn_rate : int
        number of users to spawn per second
    run_time : str
        time to run the test for
    output_folder : str
        Path to output folder
    test_name : str
        The name of test

    Returns
    -------
    None

    """
    output_files_root = output_subfolder + "/test"

    locust_command = shlex.split(
        f"""
        locust --autostart --autoquit 10
         --host {host} --locustfile {locustfile}
         -u {users} -r {spawn_rate} -t {run_time}
         --csv {output_files_root} --html {test_html_filpath}
        """
    )
    print(host)
    subprocess.run(locust_command)


def run_tests(experiment_configs, output_folder):
    """Runs a load test for each test configuration.

    Takes a dict of experiment parameters and cycles through all values for
    each parameters, running a load-test for each combination.

    Creates output folders if they don't exist.

    Parameters
    ----------
    experiment_configs : dict
        dict of experiment parameters from the config file
    output_folder : str
        Path to output folder

    Returns
    -------
    None

    """
    host = os.getenv("TARGET_URL")
    locustfile_list = experiment_configs.get("locustfile_list")
    users_list = experiment_configs.get("users_list")
    run_time_list = experiment_configs.get("run_time_list")
    # Note: default spawn-rate = n users, up to max 100 users/sec
    # as per locust's recommendations.
    spawn_rate_list = experiment_configs.get(
        "spawn_rate_list",
        [min(users, 100) for users in users_list],
    )

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(output_folder + "/html_reports", exist_ok=True)

    for locustfile in locustfile_list:
        for users_id, users in enumerate(users_list):

            run_time = run_time_list[users_id]
            spawn_rate = spawn_rate_list[users_id]

            locustfile_path = "locustfiles/" + locustfile
            test_name = (
                f"{users}_user_{locustfile[:-3]}"  # [:-3] removes .py extension
            )
            test_html_filpath = (
                f"{output_folder}/html_reports/{test_name}_report.html"
            )
            output_subfolder = f"{output_folder}/raw/{test_name}/"
            os.makedirs(output_subfolder, exist_ok=True)

            logging.info(
                f"""
                \n
                Running load-test...
                Max users: {users}
                Spawn rate: {spawn_rate}
                locustfile: {locustfile_path}
                Runtime: {run_time}
                """
            )

            run_single_test(
                host=host,
                locustfile=locustfile_path,
                users=users,
                spawn_rate=spawn_rate,
                run_time=run_time,
                output_subfolder=output_subfolder,
                test_html_filpath=test_html_filpath,
            )

            logging.info(f"{test_name} load-test completed.")

    logging.info(
        f"\n\n### ALL TESTS COMPLETE. Raw results and HTML reports saved to {output_folder} ###\n"
    )


def run_all_experiments(configs, args):
    """Runs experiments specified in configs and saves results to file.

    Parameters
    ----------
    configs : list of dicts
        List of dicts containing experiment configs
    args : dict
        Arguments from argparse

    Returns
    -------
    None

    """
    for experiment_name, experiment_configs in configs.items():
        logging.info(
            f"""
            #
            # Running experiment {experiment_name}
            #
            """
        )
        experiment_output_folder = f"{args.output}/{experiment_name}"
        run_tests(
            experiment_configs=experiment_configs,
            output_folder=experiment_output_folder,
        )
