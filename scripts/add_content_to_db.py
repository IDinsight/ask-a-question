import argparse
import csv
import os
from getpass import getpass

try:
    import requests
except ImportError:
    print(
        "Please install requests library using `pip install requests` "
        "to run this script."
    )


parser = argparse.ArgumentParser(
    description="Bulk add content to the database from a CSV file. "
    "Expects the CSV file to have columns: title, body.",
    usage="""
    python add_content_to_db.py [-h] --csv CSV --domain DOMAIN

    (example)
    python add_content_to_db.py \\
        --csv content.csv \\
        --domain aaq.idinsight.com
""",
)
parser.add_argument(
    "--csv", help="Path to the CSV file with columns: title, body", required=True
)
parser.add_argument("--domain", help="Your AAQ domain", required=True)
args = parser.parse_args()


if __name__ == "__main__":
    if not os.path.exists(args.csv):
        raise ValueError("CSV file does not exist")

    # Endpoint for obtaining the JWT
    auth_url = f"https://{args.domain}/api/login"

    # Your credentials
    username = input("Enter your username: ")
    password = getpass("Enter your password: ")  # Securely get password

    # Make a request to get the JWT
    response = requests.post(
        auth_url, data={"username": username, "password": password}
    )
    if response.status_code == 200:
        jwt_token = response.json()["access_token"]
        print("JWT Token obtained")
    else:
        print("Failed to authenticate:", response.text)

    # API endpoint
    api_endpoint = f"https://{args.domain}/api/content/"

    # Headers for the request
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

    with open(args.csv, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            payload = {
                "content_title": row["title"],
                "content_text": row["body"],
                "content_metadata": {},
            }
            response = requests.post(api_endpoint, json=payload, headers=headers)
            print(f"Status Code: {response.status_code}, Response: {response.text}")
