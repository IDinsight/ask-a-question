import json
import re

from openai import OpenAI


def create_batch_topic_query_from_template(
    topic_numbers: list[int], sample_queries: list[list[str]]
) -> str:
    """
    Creates a prompt template to ask GPT for topic descriptions.

    RETURNS
    str
        A string prompt to be passed to GPT for generating topic descriptions.
    """
    # Used for ensuring right length of list comes
    num_topics = len(topic_numbers)

    initial_context = """You are a summarization bot designed to condense multiple
    examples into a topic description specific to maternal
    health. Be concise. DO NOT GIVE A JUSTIFICATION OR PRE-AMBLE - ONLY INCLUDE THE
    TITLE OF THE TOPIC SUMMARY. 8 WORDS MAXIMUM."""

    response = """Respond in the form of a JSON structured like so:
    <Response>{"topic_list": ["First description here", "Second description here",
    "Third description here", "Fourth description here" ...]}</Response>
    "between two response tags as demonstrated."""

    number_hint = f"""HERE ARE THE {num_topics} GROUPS OF
    TOPIC + EXAMPLES QUERIES DENOTED IN TRIPLE BACKTICKS:"""

    data_string = ""
    for idx, _ in enumerate(topic_numbers):
        data_string += f"""
    ```TOPIC NUMBER {idx+1}
    SAMPLE QUERIES: {' --- '.join(sample_queries[idx])}``` """
    force_n_topics = f""""ENSURE THAT YOU HAVE {num_topics} TOPICS IN TOTAL
    AND THAT EACH TOPIC HAS A CORRESPONDING LIST OF EXAMPLE QUERIES
    AND THAT YOU ADHERE TO THE FORMAT ABOVE."""

    full_string = "\n".join(
        [initial_context, response, number_hint, data_string, force_n_topics]
    )
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
