"""
This script loads a config file, runs multiple locust load tests, plots and writes
results to file. Functionality based on: github.com/mohsenSy/locust-tests-runner/
blob/master/locust_run_tests.py
"""

import argparse
import json

from custom_load_testing import reporting, testing


def parse_args() -> argparse.Namespace:
    """Parses arguments for the script."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default="configs/1_200_ramp_config.json",
        help="JSON file containing configs for tests",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        default="outputs",
        help="Folder to store outputs",
    )
    parser.add_argument(
        "--analyze-results-only",
        action="store_true",
        help="If this tag is included, analyze previously-run test output results only",
    )
    args = parser.parse_args()

    return args


def main() -> None:
    """Run main script function."""
    args = parse_args()
    config = json.load(open(args.config))
    testing.run_tests(experiment_configs=config, output_folder=args.output)
    reporting.calculate_error_rates_and_codes(args.output)


if __name__ == "__main__":
    main()
