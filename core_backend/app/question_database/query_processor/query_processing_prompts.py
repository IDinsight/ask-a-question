# Prompts for the pipeline


def get_query_language_prompt(query_text: str) -> tuple[str, str]:
    """Create prompt to get the language of the query."""

    system_message = "You are a highly-skilled linguist and polyglot.\
              Identify the language of the user query."

    prompt = f"""
    What language is the question asked in? What script is it written in?

    Examples -
    1. "How many beds are there?". Here the language is "English" and
    the script is "Latin".

    2. "vahaan kitane bistar hain?". Here the language is "Hindi" and
    the script is "Latin".

    3. "वहाँ कितने बिस्तर हैं?". Here the language is "Hindi" and
    the script is "Devanagari".

    Here is a question from a field employee -
    ### Question
    <<<{query_text}>>>

    Take a deep breath and work through the problem step-by-step

    Only, reply in a python parsable json with key "language"
    value being the language and "script" value being the script.
    """
    return system_message, prompt


def create_best_tables_prompt(query_model: dict, table_description: str) -> str:
    """Create prompt for best tables question."""
    prompt = f"""
    ===== Question =====
    <<< {query_model["query_text"]} >>>

    ===== Metadata =====
    Here is useful metadata (might be empty if not available):
    <<< {query_model["query_metadata"]} >>>

    ==== Source =====
    Which of the following sources of information are you going to use to
    answer the question. Select all that are relevant:
    {table_description}

    ===== Answer Format =====
    python parsable json with key "response_sources". Tables in a list.

    ==== Remember ====
    The person who is asking the question does not know about different codes or ids.
    Identify all information we would need to answer their question in names
    and numbers in natural language.
    """

    return prompt


def create_best_columns_prompt(
    query_model: dict, relevant_schemas: str, columns_description: str
) -> str:
    """Create prompt for best columns question."""
    prompt = f"""
    Here is a question from a field employee who aims to
    identify and enrol out of school girls based on the data in the database.

    ===== Question =====
    <<< {query_model["query_text"]} >>>

    ===== Metadata =====
    Here is useful metadata (might be empty if not available):
    <<< {query_model["query_metadata"]} >>>

    ===== Relevant Tables =====
    Here is the tables schema of the relevant tables

    <<< {relevant_schemas} >>>

    ===== Columns =====
    Here is the description of columns (Might be empty if not available)
    <<< {columns_description} >>>

    ==== Relevant Columns =====
    Based on the above schema, which columns should we use to answer the question?
    It is much better to select more columns than less because the cost of
    omissions is high.

    ==== Response format ====
    python parsable json where each table is a key and the value is a list of columns.
    """

    return prompt


def create_sql_generating_prompt(
    query_model: dict,
    relevant_schemas: str,
    top_k_common_values: str,
    columns_description: str,
    num_common_values: int,
) -> str:
    """Create prompt for generating SQL query."""
    prompt = f"""
    ===== Question =====
    <<< {query_model["query_text"]} >>>

    ===== Metadata =====
    Here is useful metadata (might be empty if not available):
    <<< {query_model["query_metadata"]} >>>

    ===== Relevant Tables =====
    The query will run on a database with the following schema:
    <<<{relevant_schemas}>>>

    ===== Relevant Columns =====
    Here is the description of columns (Might be empty if not available)
    <<< {columns_description} >>>

    ===== {num_common_values} most common values in potentially relevant columns =====
    <<<{top_k_common_values}>>>


    ==== Instruction ====
    Given the above, generate a SQL query that will user's query.

    Always create a SQL query that will run on the above schema.

    Always use the query metadata to construct the SQL query.

    ===== Answer Format =====
    python parsable json with the key being "sql" and value being the sql code.
    """

    return prompt


def create_final_answer_prompt(
    query_model: dict,
    final_sql_code_to_run: str,
    final_sql_response: list,
    language: str,
    script: str,
) -> str:
    """Create prompt for final answer."""
    prompt = f"""
    Here is a question from a field employee -
    ### Question
    <<< {query_model["query_text"]} >>>

    ===== Metadata =====
    Here is useful metadata (might be empty if not available):
    <<< {query_model["query_metadata"]} >>>

    Here is a SQL query generated to answer that question -
    <<<{final_sql_code_to_run}>>>

    Here is the response to the SQL query from the DB -
    <<<{final_sql_response}>>>

    ===== Instruction =====
    Use the above information to create a final response for the field employee's
    question.

    Always construct an answer that is as specific to the user as possible. Use the
    query metadata to do this.

    Use ALL the information in the response to the SQL query to answer accurately
    while also explaining how the answer was generated to the person who asked the
    question. Take care to reproduce decimals and fractions accurately.

    ===== Answer Format =====
    python parsable json with only one key "answer".

    Answer in {language} in the {script} script in the same
    mannerisms as the question.

    Remember, the field employees don't know what SQL is
    but are roughly familiar with what data is being
    collected a high level.
    """

    return prompt
