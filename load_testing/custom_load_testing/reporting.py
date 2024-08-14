import csv
import logging
import os


def calculate_error_rates_and_codes(output_folder: str) -> None:
    """Calculate error rates and unique error codes from the output CSV files.

    Parameters
    ----------
    output_folder : str
        Path to output folder

    Returns
    -------
    None
    """
    raw_output_folder = os.path.join(output_folder, "raw")
    for root, _, files in os.walk(raw_output_folder):
        for file in files:
            if file == "test_stats.csv":
                stats_file_path = os.path.join(root, file)
                failures_file_path = os.path.join(root, "test_failures.csv")

                total_requests = 0
                total_failures = 0
                unique_error_codes = set()

                # Read the stats file to get total requests and failures
                with open(stats_file_path, mode="r") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        total_requests += int(row["Request Count"])
                        total_failures += int(row["Failure Count"])

                # Read the failures file to get unique error codes
                if os.path.exists(failures_file_path):
                    with open(failures_file_path, mode="r") as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            unique_error_codes.add(row["Error"])
                if total_requests > 0:
                    error_rate = (total_failures / total_requests) * 100
                else:
                    error_rate = 0
                if not unique_error_codes:
                    unique_error_codes.add("None")
                logging.info(f"Test: {root}")
                logging.info(f"Error Rate: {error_rate:.2f}%")
                logging.info(f"Unique Error Codes: {unique_error_codes}")
