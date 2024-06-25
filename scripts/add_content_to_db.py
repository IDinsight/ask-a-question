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
        auth_url, data={"username": username, "password": password}, verify=False
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
        tags = [val.upper() for row in reader for val in eval(row["faq_tags"])]
        tags_db = requests.get(
            tags_endpoint,
            headers=headers,
            verify=False,
        )
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
                tags_endpoint, json=payload, headers=headers, verify=False
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
            if args.language:
                language = args.language
            else:
                language = row["language"]
            content_tags = [tags_map[val.upper()] for val in eval(row["faq_tags"])]
            payload = {
                "content_title": row["faq_title"],
                "content_text": row["faq_content_to_send"],
                "content_language": language,
                "content_tags": content_tags,
                "content_metadata": {},
            }
            response = requests.post(
                contents_endpoint, json=payload, headers=headers, verify=False
            )
            print(f"Status Code: {response.status_code}, Response: {response.text}")
