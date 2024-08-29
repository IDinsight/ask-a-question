import argparse
import json
import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import urllib3
from add_users_to_db import ADMIN_API_KEY
from app.config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_GENERATION,
)
from app.contents.models import ContentDB
from app.database import get_session
from app.llm_call.utils import remove_json_markdown
from app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    QueryResponseContentDB,
    ResponseFeedbackDB,
)
from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from app.users.models import UserDB
from app.utils import get_key_hash
from litellm import completion
from sqlalchemy import (
    select,
)
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
    (QueryResponseContentDB, "created_datetime_utc"),
    (UrgencyQueryDB, "message_datetime_utc"),
    (UrgencyResponseDB, "response_datetime_utc"),
]

parser = argparse.ArgumentParser(
    description="Bulk add data to the database.",
    usage="""
    python add_content_to_db.py [-h] --csv CSV --domain DOMAIN [--language LANGUAGE]

    (example)
    python add_new_dummy_data.py \
        --csv generated_questions.csv \
        --host http://localhost:8000 \
        --api-key <API_KEY> \
        --nb-workers 8 \
        --start-date 01-08-23

""",
)
parser.add_argument(
    "--csv", help="Path to the CSV containing example questions ", required=True
)
parser.add_argument("--host", help="Your hosted AAQ url", required=True)
parser.add_argument("--api-key", help="Your AAQ API key", required=False)
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
        model=LITELLM_MODEL_GENERATION,
        api_base=LITELLM_ENDPOINT,
        api_key=LITELLM_API_KEY,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7,
    )

    try:
        # Extract the output from the response
        feedback_output = response["choices"][0]["message"]["content"].strip()
        feedback_output = remove_json_markdown(feedback_output)
        feedback_dict = json.loads(feedback_output)
        if isinstance(feedback_dict, dict) and "output" in feedback_dict:
            return feedback_dict
        else:
            raise ValueError("Output is not in the correct format.")
    except Exception as e:
        print(f"Output is not in the correct format.{e}")
        return None


def save_single_row(endpoint: str, data: dict, retries: int = 2) -> dict | None:
    """
    Save a single row in the database.
    """
    try:
        response = requests.post(
            endpoint,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            json=data,
            verify=False,
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        if retries > 0:
            # Implement exponential wait before retrying
            time.sleep(2 ** (2 - retries))
            return save_single_row(endpoint, data, retries=retries - 1)
        else:
            print(f"Request failed after retries: {e}")
            return None


def process_search(_id: int, text: str) -> tuple | None:
    """
    Process and add query to DB
    """

    endpoint = f"{HOST}/search"
    data = {
        "query_text": text,
        "generate_llm_response": False,
        "generate_tts": False,
    }
    response = save_single_row(endpoint, data)
    if response and isinstance(response, dict) and "search_results" in response:
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

    endpoint = f"{HOST}/response-feedback"

    if is_off_topic and feedback_sentiment == "positive":
        return None

    data = {
        "query_id": query_id,
        "feedback_sentiment": feedback_sentiment,
        "feedback_secret_key": feedback_secret_key,
    }

    response = (
        save_single_row(endpoint, data) if not pd.isna(feedback_sentiment) else None
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
    endpoint = f"{HOST}/content-feedback"

    if is_off_topic and feedback_sentiment == "positive":
        return None
    # randomly get a content from the search results to provide feedback on
    content_num = str(random.randint(0, 3))
    if not search_results or not isinstance(search_results, dict):
        return None
    if content_num not in search_results:
        return None

    content = search_results[content_num]

    # Get content text and use to generate feedback text using LLMs
    content_text = content["title"] + " " + content["text"]
    generated_text = generate_feedback(query_text, content_text, feedback_sentiment)

    feedback_text = (
        generated_text["output"]
        if generate_feedback_text and generated_text is not None
        else ""
    )

    data = {
        "query_id": query_id,
        "content_id": content["id"],
        "feedback_sentiment": feedback_sentiment,
        "feedback_text": feedback_text,
        "feedback_secret_key": feedback_secret_key,
    }
    response = (
        save_single_row(endpoint, data) if not pd.isna(feedback_sentiment) else None
    )
    if response is not None:
        return (query_id,)

    return None


def process_urgency_detection(_id: int, text: str) -> tuple | None:
    """
    Process and add urgency detection to DB
    """
    endpoint = f"{HOST}/urgency-detect"
    data = {
        "message_text": text,
    }

    response = save_single_row(endpoint, data)
    if response and "is_urgent" in response:
        return (response["is_urgent"],)
    return None


def create_random_datetime_from_string(start_date: datetime) -> datetime:
    """
    Create a random datetime from a date in the format "%d-%m-%y
    to today
    """

    time_difference = datetime.now() - start_date
    random_number_of_days = random.randint(0, time_difference.days)

    random_number_of_seconds = random.randint(0, 86399)  # Number of seconds in one day

    random_datetime = start_date + timedelta(
        days=random_number_of_days, seconds=random_number_of_seconds
    )
    return random_datetime


def update_date_of_records(models: list, random_dates: list, api_key: str) -> None:
    """
    Update the date of the records in the database
    """
    session = next(get_session())
    hashed_token = get_key_hash(api_key)
    user = session.execute(
        select(UserDB).where(UserDB.hashed_api_key == hashed_token)
    ).scalar_one()
    queries = [c for c in session.query(QueryDB).all() if c.user_id == user.user_id]
    if len(queries) > len(random_dates):
        random_dates = random_dates + [
            create_random_datetime_from_string(start_date)
            for _ in range(len(queries) - len(random_dates))
        ]
    # Create a dictionary to map the query_id to the random date
    date_map_dic = {queries[i].query_id: random_dates[i] for i in range(len(queries))}
    for model in models:
        print(f"Updating the date of the records for {model[0].__name__}...")
        session = next(get_session())

        rows = [c for c in session.query(model[0]).all() if c.user_id == user.user_id]

        for i, row in enumerate(rows):
            # Set the date attribute to the random date
            if hasattr(row, "query_id"):
                date = date_map_dic[row.query_id]
            else:
                date = random_dates[i]
            setattr(row, model[1], date)
            session.merge(row)
        session.commit()


def update_date_of_contents(date: datetime) -> None:
    """
    Update the date of the content records in the database for consistency
    """
    session = next(get_session())
    contents = session.query(ContentDB).all()
    for content in contents:
        content.created_datetime_utc = date
        content.updated_datetime_utc = date
        session.merge(content)
    session.commit()


if __name__ == "__main__":
    HOST = args.host
    NB_WORKERS = int(args.nb_workers) if args.nb_workers else 8
    API_KEY = args.api_key if args.api_key else ADMIN_API_KEY

    date_string = args.start_date if args.start_date else "01-08-23"
    date_format = "%d-%m-%y"
    start_date = datetime.strptime(date_string, date_format)
    assert (
        start_date and start_date < datetime.now()
    ), "Invalid start date. Please provide a valid start date."

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
                print(f"Search Query successfully added for query_id: {result[1]}")
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
            for query_id, message_text in zip(df["inbound_id"], df["inbound_text"])
        }
        for future in as_completed(future_to_text):
            result = future.result()
        print("Urgency Detection successfully processed")

    random_dates = [
        create_random_datetime_from_string(start_date) for _ in range(len(df))
    ]
    print("Updating the date of the records...")
    update_date_of_records(MODELS, random_dates, API_KEY)

    print("Updating the date of the content records...")
    update_date_of_contents(start_date)
    print("All records dates updated successfully.")
    print("All records added successfully.")
