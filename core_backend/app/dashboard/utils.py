import json
import re

from bertopic import BERTopic
from openai import OpenAI


def fetch_five_sample_queries(
    topic_num: int, original_queries: list[str], topic_model: BERTopic
) -> list[str]:
    """
    Fetches five sample queries corresponding to a given topic.

    Parameters
    ----------
    topic_num : int
        The topic number to fetch sample queries for.
    original_queries : list[str]
        The list of original queries that were clustered into topics.
    topic_model : Any
        The topic model object used to classify and extract queries.

    Returns
    -------
    list[str]
        A list of five sample queries for the given topic.
    """
    queries = (
        topic_model.get_document_info(original_queries)
        .query(f"Topic=={topic_num}")
        .sample(5)
        .Document.tolist()
    )
    return queries


def create_topic_query_from_template(
    representation: list[list[str]], sample_queries: list[list[str]]
) -> str:
    """
    Creates a prompt template to ask GPT for topic descriptions.

    Parameters
    ----------
    representation : list[list[str]]
        A list containing lists of keywords representing each topic.
    sample_queries: list[list[str]]
        A list containing lists of sample queries for each topic.

    Returns
    -------
    str
        A string prompt to be passed to GPT for generating topic descriptions.
    """
    initial_context = (
        "You are a summarization bot designed to condense multiple examples "
        "alongside some keywords into a topic description specific to maternal health. "
        "Be concise. DO NOT GIVE A JUSTIFICATION OR PRE-AMBLE - ONLY INCLUDE THE TITLE "
        "OF THE TOPIC SUMMARY. 8 WORDS MAXIMUM."
    )

    response = """Respond in the form of a LIST OF JSONs structured like so:
    <Response>{"topic_list": ["Topic 1 description here", "Topic 2 description here",
    "Topic 3 description here", "Topic 4 description here",
    "Topic 5 description here"]}</Response>
    "between two response tags as demonstrated. HERE ARE THE FIVE GROUPS OF
    KEYWORDS AND EXAMPLES OF QUERIES DENOTED IN TRIPLE BACKTICKS:"""

    data_string = ""
    for x in range(1, 6):
        data_string += f"""
    ```TOPIC {str(x)} KEYWORDS {' '.join(representation[x-1])} + TOPIC {str(x)}
    SAMPLE QUERIES: {' --- '.join(sample_queries[x-1])}``` """

    full_string = "\n".join([initial_context, response, data_string])
    return full_string


def parse_answer(llm_response: str) -> dict[str, list[str]]:
    """
    Parses the JSON response from the GPT model for topic descriptions.

    Parameters
    ----------
    llm_response : str
        The response from the GPT model containing the topic descriptions.

    Returns
    -------
    dict[str, list[str]]
        A dictionary containing the parsed topic descriptions.
    """
    # Define the tag name as a variable
    tag = "Response"

    # Create the regex pattern with string formatting
    pattern = rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>"

    # Use the pattern in re.findall
    results = re.findall(pattern, llm_response)

    if results:
        return json.loads(results[0])
    else:
        return {}


def ask_question(prompt: str) -> dict[str, list[str]]:
    """
    Sends a prompt to GPT and returns the generated topic descriptions.

    Parameters
    ----------
    prompt : str
        The prompt string to be passed to GPT.

    Returns
    -------
    dict[str, list[str]]
        A dictionary containing the topic descriptions generated by GPT.
    """
    client = OpenAI()
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{prompt}"},
        ],
        temperature=0,
        n=1,
    )

    return parse_answer(completion.choices[0].message.content)
