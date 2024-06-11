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
    "Expects the CSV file to have columns: title, body. (Optionally, language. "
    "See also the --language option.)",
    usage="""
    python add_content_to_db.py [-h] --csv CSV --domain DOMAIN [--language LANGUAGE]

    (example)
    python add_content_to_db.py \\
        --csv content.csv \\
        --domain aaq.idinsight.com \\
        --language ENGLISH
""",
)
parser.add_argument(
    "--csv", help="Path to the CSV file with columns: title, body", required=True
)
parser.add_argument("--domain", help="Your AAQ domain", required=True)
parser.add_argument(
    "--language",
    help="Language of the content, if it is the same for the whole file.",
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
        tags = [val for row in reader for val in row["tags"].strip().split(" ")]
        print(tags)
        tags = set(tags)
        tags_map = {}
        for tag in tags:
            payload = {
                "tag_name": tag,
            }
            response = requests.post(tags_endpoint, json=payload, headers=headers)
            if "tag_id" not in response.json():
                print(f"Failed to create tag: {tag}")
                continue
            response_json = response.json()
            tags_map[response_json["tag_name"]] = response_json["tag_id"]
            print(f"Status Code: {response.status_code}, Response: {response.text}")
        file.seek(0)
        reader = csv.DictReader(file)
        for row in reader:
            if args.language:
                language = args.language
            else:
                language = row["language"]
            content_tags = [
                tags_map[val] for val in row["tags"].strip().upper().split(" ")
            ]
            payload = {
                "content_title": row["title"],
                "content_text": row["body"],
                "content_language": language,
                "content_tags": content_tags,
                "content_metadata": {},
            }
            response = requests.post(contents_endpoint, json=payload, headers=headers)
            print(f"Status Code: {response.status_code}, Response: {response.text}")
