from pydantic import BaseModel, ConfigDict


class DashboardQueryBase(BaseModel):
    """
    Pydantic model for dashboard query
    """

    query_text: str
    query_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class Prompts(BaseModel):
    """
    Pydantic model for prompts
    """

    final_answer_prompt: str | None
    sql_prompt: str | None
    best_columns_prompt: str | None
    best_tables_prompt: str | None
    language_prompt: str | None
    prompt_to_generate_sql: str | None

    model_config = ConfigDict(from_attributes=True)


class DashboardQueryResponse(BaseModel):
    """
    Pydantic model for response to dashboard query
    """

    best_tables: list[str] | str
    query_language: str
    query_script: str
    best_columns: dict | str
    sql_query: str
    text_response: str
    total_cost: float
    processing_cost: float
    guardrails_cost: float
    guardrails_status: dict
    schema_used: str
    prompts: Prompts
    model_used: str
    guardrails_model: str

    model_config = ConfigDict(from_attributes=True)
