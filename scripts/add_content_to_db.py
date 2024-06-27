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
    python add_content_to_db.py [-h] --csv CSV --domain DOMAIN --verify [True/False]

    (example)
    python add_content_to_db.py \\
        --csv content.csv \\
        --domain aaq.idinsight.com \\
        --verify True
""",
)
parser.add_argument(
    "--csv", help="Path to the CSV file with columns: title, body", required=True
)
parser.add_argument("--domain", help="Your AAQ domain", required=True)
parser.add_argument(
    "--verify",
    help="True if we want to verify certificates, False otherwise",
    type=lambda x: (str(x).lower() in ["true", "1", "yes"]),
    required=True,
    default=True,
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
    verify = bool(args.verify)
    print(type(args.verify))
    # Make a request to get the JWT
    response = requests.post(
        auth_url, data={"username": username, "password": password}, verify=verify
    )
    if response.status_code == 200:
        jwt_token = response.json()["access_token"]
        print("JWT Token obtained")
    else:
        raise ValueError("Failed to authenticate:", response.text)

    # API endpoint
    contents_endpoint = f"https://{args.domain}/api/content/"
    tags_endpoint = f"https://{args.domain}/api/tag/"
    # Headers for the request
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

    with open(args.csv, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        tags = [val.upper() for row in reader for val in row["tags"].split(",")]
        tags_db = requests.get(tags_endpoint, headers=headers, verify=verify)
        tags_map = {val["tag_name"]: val["tag_id"] for val in tags_db.json()}

        tags_db = [val["tag_name"] for val in tags_db.json()]
        tags = set(tags) - set(tags_db)
        if len(tags) > 0:
            print(f"Adding new tags: {tags}")

            for tag in tags:
                payload = {
                    "tag_name": tag,
                }
                response = requests.post(
                    tags_endpoint, json=payload, headers=headers, verify=verify
                )
                print(f"Status Code: {response.status_code}, Response: {response.text}")

                if "tag_id" not in response.json():
                    raise ValueError("Could not create tag: {tag}.")
                response_json = response.json()
                tags_map[response_json["tag_name"]] = response_json["tag_id"]
        else:
            print("No new tags to add.")
        file.seek(0)
        reader = csv.DictReader(file)
        for row in reader:
            content_tags = [tags_map[val.upper()] for val in row["tags"].split(",")]
            payload = {
                "content_title": row["title"],
                "content_text": row["body"],
                "content_tags": content_tags,
                "content_metadata": {},
            }
            response = requests.post(
                contents_endpoint, json=payload, headers=headers, verify=verify
            )
            print(f"Status Code: {response.status_code}, Response: {response.text}")
