from uuid import uuid4

from fastapi import APIRouter, Depends

from .auth import auth_bearer_token
from .query_processor.query_processor import LLMQueryProcessor
from .schemas import Prompts, UserQueryBase, UserQueryResponse
from .utils import setup_logger

flow_logger = setup_logger("Flow Logger")

router = APIRouter(prefix="/ask-database", tags=["Ask Database"])


@router.post("/get-metric")
async def get_metric(
    user_query: UserQueryBase,
    auth_response: dict = Depends(auth_bearer_token),
) -> UserQueryResponse:
    """
    Path operation to answer user query

    Args:
        user_query (UserQueryBase): The user query
        auth_response (dict): The auth response dictionary
            containing the async session and settings.
    """
    feedback_secret_key = generate_secret_key()
    asession_sql = auth_response["async_session"]
    db_settings = auth_response["settings"]

    qp = LLMQueryProcessor(
        query=user_query.model_dump(),
        asession=asession_sql,
        llm=db_settings.LLM_MODEL,
        which_db=db_settings.WHICH_DB,
        guardrails_llm=db_settings.GUARDRAILS_LLM_MODEL,
        sys_message=db_settings.SYSTEM_MESSAGE,
        db_description=db_settings.METRIC_DB_TABLE_DESCRIPTION,
        column_description=db_settings.METRIC_DB_COLUMN_DESCRIPTION,
        num_common_values=db_settings.NUM_COMMON_VALUES,
    )
    await qp.process_query()

    if hasattr(qp, "timings"):
        flow_logger.debug(f"Query processing time: {qp.timings}")  # type: ignore
    if hasattr(qp.tools, "timings"):
        flow_logger.debug(f"Table Schema time: {qp.tools.timings}")  # type: ignore

    # Return response
    response = UserQueryResponse(
        query_language=qp.query_language,
        query_script=qp.query_script,
        best_tables=qp.best_tables,
        best_columns=qp.best_columns,
        sql_query=qp.sql_query,
        text_response=qp.final_answer,
        total_cost=qp.cost + qp.guardrails.cost,
        processing_cost=qp.cost,
        guardrails_cost=qp.guardrails.cost,
        guardrails_status=qp.guardrails.guardrails_status,
        schema_used=qp.relevant_schemas,
        feedback_secret_key=feedback_secret_key,
        prompts=Prompts(
            language_prompt=qp.language_prompt,
            best_tables_prompt=qp.best_tables_prompt,
            best_columns_prompt=qp.best_columns_prompt,
            sql_prompt=qp.sql_generating_prompt,
            final_answer_prompt=qp.final_answer_prompt,
            prompt_to_generate_sql=qp.sql_generating_prompt,
        ),
        model_used=qp.llm,
        guardrails_model=qp.guardrails.guardrails_llm,
    )

    return response


def generate_secret_key() -> str:
    """
    Generate a secret key for the user query
    """
    return uuid4().hex
