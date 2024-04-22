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


parser = argparse.ArgumentParser()
parser.add_argument("--csv", help="Path to the CSV file", required=True)
parser.add_argument("--domain", help="Your AAQ domain", required=True)
parser.add_argument(
    "--language",
    help="Language of the content, if it is the same for the whole file",
    required=False,
)
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
    api_endpoint = f"https://{args.domain}/api/content/create"

    # Headers for the request
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

    with open(args.csv, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if args.language:
                language = args.language
            else:
                language = row["language"]

            payload = {
                "content_title": row["title"],
                "content_text": row["body"],
                "content_language": language,
                "content_metadata": {},
            }
            response = requests.post(api_endpoint, json=payload, headers=headers)
            print(f"Status Code: {response.status_code}, Response: {response.text}")
