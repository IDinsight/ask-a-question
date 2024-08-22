import argparse
import json
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import urllib3
from add_users_to_db import ADMIN_API_KEY
from app.config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_DEFAULT,
)
from app.database import get_session
from app.question_answer.models import ContentFeedbackDB, QueryDB, ResponseFeedbackDB
from app.urgency_detection.models import UrgencyQueryDB
from litellm import completion
from urllib3.exceptions import InsecureRequestWarning

# To disable InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

try:
    import requests  # type: ignore
except ImportError:
    print(
        "Please install requests library using `pip install requests` "
        "to run this script."
    )

MODELS = [
    (QueryDB, "query_datetime_utc"),
    (ResponseFeedbackDB, "feedback_datetime_utc"),
    (ContentFeedbackDB, "feedback_datetime_utc"),
    (UrgencyQueryDB, "message_datetime_utc"),
]

parser = argparse.ArgumentParser(
    description="Bulk add data to the database.",
    usage="""
    python add_content_to_db.py [-h] --csv CSV --domain DOMAIN [--language LANGUAGE]

    (example)
    python add_new_dummy_data.py \\
        --csv generated_questions.csv \\
        --host localhost:8000 \\
        --nb-workers 8 \\
        --start-date 01-08-23

""",
)
parser.add_argument("--csv", help="Path to the CSV ", required=True)
parser.add_argument("--domain", help="Your AAQ domain", required=True)
parser.add_argument(
    "--nb-workers",
    help="Number of workers to use for parallel processing",
    required=False,
)
parser.add_argument(
    "--start-date",
    help="Start date for the records in the format dd-mm-yy",
    required=False,
)
args = parser.parse_args()


def generate_feedback(question_text: str, faq_text: str, sentiment: str) -> dict | None:
    """
    Generate feedback based on the user's question and the FAQ response.
    """
    # Define the prompt
    prompt = f"""
    You are an AI model that helps generate feedback based on a user's question and an
    FAQ response.
    The feedback should be a follow up of the user on how well the response answered
    their question and the feedback should be on the first person.
    If the response is inaccurate, incomplete, or irrelevant the feedback should be
    a clarification.
    If the response is accurate, complete, and relevant the feedback should be
    a confirmation.
    The feedback should also be tailored to the sentiment of the user's question and
    should be short and concise especially when the feedback is positive.
    Your output should strictly adhere to the following format

    {{"output":"<feedback_text>"}}

    Here are the inputs:
    - Question: "{question_text}"
    - FAQ: "{faq_text}"
    - Sentiment: "{sentiment}"  // The sentiment can be "positive" or "negative"

    Generate the feedback text based on the sentiment and input.

    Output:
    """

    response = completion(
        model=LITELLM_MODEL_DEFAULT,
        api_base=LITELLM_ENDPOINT,
        api_key=LITELLM_API_KEY,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7,
    )

    # Extract the output from the response
    feedback_output = response["choices"][0]["message"]["content"].strip()
    feedback_output = feedback_output.replace("json", "")
    feedback_output = feedback_output.replace("\n", "").strip()

    try:
        feedback_dict = json.loads(feedback_output)
        if isinstance(feedback_dict, dict) and "output" in feedback_dict:

            return feedback_dict
        else:
            raise ValueError("Output is not in the correct format.")
    except (SyntaxError, ValueError) as e:
        print(f"Output is not in the correct format.{e}")
        return None


def process_search(_id: int, text: str) -> tuple | None:
    """
    Process and add query to DB
    """

    def save_single_query(query: str) -> dict:
        """
        Save the query in the database.
        """
        endpoint = f"{HOST}/search"
        data = {
            "query_text": query,
            "session_id": 0,
            "generate_llm_response": False,
            "query_metadata": {"some_key": "some_value"},
            "generate_tts": False,
        }
        response = requests.post(
            endpoint,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ADMIN_API_KEY}",
            },
            json=data,
            verify=False,
        )
        return response.json()

    response = save_single_query(text)
    if "search_results" in response:
        return (
            _id,
            response["query_id"],
            response["feedback_secret_key"],
            response["search_results"],
        )
    return None


def process_response_feedback(
    query_id: int, feedback_sentiment: str, feedback_secret_key: str, is_off_topic: bool
) -> tuple | None:
    """
    Process and add response feedback to DB
    """

    def save_single_response_feedback(
        query_id: int, feedback_sentiment: str, feedback_secret_key: str
    ) -> dict:
        """
        Save the query in the database.
        """
        endpoint = f"{HOST}/response-feedback"
        data = {
            "query_id": query_id,
            "session_id": 0,
            "feedback_sentiment": feedback_sentiment,
            "feedback_text": "",
            "feedback_secret_key": feedback_secret_key,
        }
        response = requests.post(
            endpoint,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ADMIN_API_KEY}",
            },
            json=data,
            verify=False,
        )
        return response.json()

    if is_off_topic and feedback_sentiment == "positive":
        return None
    response = (
        save_single_response_feedback(query_id, feedback_sentiment, feedback_secret_key)
        if not pd.isna(feedback_sentiment)
        else None
    )
    if response is not None:
        return (query_id,)

    return None


def process_content_feedback(
    query_id: int,
    query_text: str,
    search_results: dict,
    feedback_sentiment: str,
    feedback_secret_key: str,
    is_off_topic: bool,
    generate_feedback_text: bool,
) -> tuple | None:
    """
    Process and add content feedback to DB
    """

    def save_single_content_feedback(
        query_id: int,
        content_id: int,
        feedback_sentiment: str,
        feedback_text: str,
        feedback_secret_key: str,
    ) -> dict:
        """
        Save the feedback in the database.
        """
        endpoint = f"{HOST}/content-feedback"
        data = {
            "query_id": query_id,
            "session_id": 0,
            "content_id": content_id,
            "feedback_sentiment": feedback_sentiment,
            "feedback_text": feedback_text,
            "feedback_secret_key": feedback_secret_key,
        }
        response = requests.post(
            endpoint,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ADMIN_API_KEY}",
            },
            json=data,
            verify=False,
        )
        return response.json()

    if is_off_topic and feedback_sentiment == "positive":
        return None
    # randomly get a content from the search results to provide feedback on
    content = search_results[str(random.randint(0, 3))]

    # Get content text and use to generate feedback text using LLMs
    content_text = content["title"] + " " + content["text"]
    generated_text = generate_feedback(query_text, content_text, feedback_sentiment)

    feedback_text = (
        generated_text["output"]
        if generate_feedback_text and generated_text is not None
        else ""
    )

    response = (
        save_single_content_feedback(
            query_id,
            content["id"],
            feedback_sentiment,
            feedback_text,
            feedback_secret_key,
        )
        if not pd.isna(feedback_sentiment)
        else None
    )
    if response is not None:
        return (query_id,)

    return None


def process_urgency_detection(_id: int, text: str) -> tuple | None:
    """
    Process and add urgency detection to DB
    """

    def save_single_ud_query(query: str) -> dict:
        """
        Save the query in the database.
        """
        endpoint = f"{HOST}/urgency-detect"
        data = {
            "message_text": query,
        }
        response = requests.post(
            endpoint,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ADMIN_API_KEY}",
            },
            json=data,
            verify=False,
        )
        return response.json()

    response = save_single_ud_query(text)
    if "is_urgent" in response:
        return (response["is_urgent"],)
    return None


def create_random_datetime_from_string(date_string: str) -> datetime:
    """
    Create a random datetime from a date in the format "%d-%m-%y
    to today
    """
    date_format = "%d-%m-%y"

    start_date = datetime.strptime(date_string, date_format)

    time_difference = datetime.now() - start_date
    random_number_of_days = random.randint(0, time_difference.days)

    random_number_of_seconds = random.randint(0, 86399)  # Number of seconds in one day

    random_datetime = start_date + timedelta(
        days=random_number_of_days, seconds=random_number_of_seconds
    )
    return random_datetime


def update_date_of_records(models: list, random_dates: list) -> None:
    """
    Update the date of the records in the database
    """
    session = next(get_session())

    for model in models:
        session = next(get_session())
        queries = [c for c in session.query(model[0]).all()]
        if len(queries) > len(random_dates):
            random_dates = random_dates + [
                create_random_datetime_from_string(start_date)
                for _ in range(len(queries) - len(random_dates))
            ]
        for query, date in zip(queries, random_dates):
            # Set the date attribute to the random date
            setattr(query, model[1], date)
            session.merge(query)
        session.commit()


if __name__ == "__main__":
    HOST = auth_url = (
        f"https://{args.domain}" if args.domain else "http://localhost/api"
    )
    NB_WORKERS = int(args.nb_workers) if args.nb_workers else 8
    path = args.csv
    df = pd.read_csv(path)

    saved_queries = defaultdict(list)
    print("Processing search queries...")
    # Using multithreading to speed up the process
    with ThreadPoolExecutor(max_workers=NB_WORKERS) as executor:
        future_to_text = {
            executor.submit(process_search, _id, text): _id
            for _id, text in zip(df["inbound_id"], df["inbound_text"])
        }
        for future in as_completed(future_to_text):
            result = future.result()
            if result:
                saved_queries["inbound_id"].append(result[0])
                saved_queries["query_id"].append(result[1])
                saved_queries["feedback_secret_key"].append(result[2])
                saved_queries["search_results"].append(result[3])

    saved_queries_df = pd.DataFrame(saved_queries)
    df = df.merge(saved_queries_df, on="inbound_id", how="left")

    print("Processing response feedback...")
    with ThreadPoolExecutor(max_workers=NB_WORKERS) as executor:
        future_to_text = {
            executor.submit(
                process_response_feedback,
                query_id,
                feedback_sentiment,
                feedback_secret_key,
                is_off_topic,
            ): query_id
            for query_id, feedback_sentiment, feedback_secret_key, is_off_topic in zip(
                df["query_id"],
                df["response_feedback"],
                df["feedback_secret_key"],
                df["is_off_topic"],
            )
        }
        for future in as_completed(future_to_text):
            result = future.result()
            if result:
                print(f"Response Feedback successfully added for query_id: {result[0]}")

    print("Processing content feedback...")
    with ThreadPoolExecutor(max_workers=NB_WORKERS) as executor:
        future_to_text = {
            executor.submit(
                process_content_feedback,
                query_id,
                text,
                srch_res,
                fbk_stmt,
                fbk_key,
                gen_fbk_txt,
                is_off,
            ): query_id
            for query_id, text, srch_res, fbk_stmt, fbk_key, gen_fbk_txt, is_off in zip(
                df["query_id"],
                df["inbound_text"],
                df["search_results"],
                df["response_feedback"],
                df["feedback_secret_key"],
                df["generate_feedback_text"],
                df["is_off_topic"],
            )
        }
        for future in as_completed(future_to_text):
            result = future.result()
            if result:
                print(f"Content Feedback successfully added for query_id: {result[0]}")

    print("Processing urgency detection...")
    with ThreadPoolExecutor(max_workers=NB_WORKERS) as executor:
        future_to_text = {
            executor.submit(
                process_urgency_detection,
                query_id,
                message_text,
            ): query_id
            for query_id, message_text in zip(df["query_id"], df["inbound_text"])
        }
        for future in as_completed(future_to_text):
            result = future.result()
        print("Urgency Detection successfully processed")

    start_date = args.start_date if args.start_date else "01-08-23"
    random_dates = [
        create_random_datetime_from_string(start_date) for _ in range(len(df))
    ]
    print("Updating the date of the records...")
    update_date_of_records(MODELS, random_dates)
    print("All records dates updated successfully.")
    print("All records added successfully.")
