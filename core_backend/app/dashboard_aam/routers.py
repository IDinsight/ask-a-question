from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..llm_call.llm_prompts import (
    DASHBOARD_DB_TABLE_DESCRIPTION,
    DASHBOARD_SYSTEM_MESSAGE,
)
from ..users.models import UserDB
from ..utils import setup_logger
from .query_processor.query_processor import LLMQueryProcessor
from .schemas import DashboardQueryBase, DashboardQueryResponse, Prompts

logger = setup_logger("Ask dashboard")


TAG_METADATA = {
    "name": "Ask dashboard",
    "description": "_Requires user login._ Ask questions about your AAQ dashboard"
    "data.",
}


router = APIRouter(prefix="/ask-dashboard", tags=[TAG_METADATA["name"]])


@router.post("/get-metric")
async def get_metric(
    user_query: DashboardQueryBase,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardQueryResponse:
    """
    Answers user query about AAQ data.
    """
    qp = LLMQueryProcessor(
        query=user_query.model_dump(),
        asession=asession,
        user_id=user_db.user_id,
        sys_message=DASHBOARD_SYSTEM_MESSAGE,
        db_description=DASHBOARD_DB_TABLE_DESCRIPTION,
        column_description="",  # TODO: find out what this does
        num_common_values=10,  # TODO: find out what this does
    )
    await qp.process_query()

    if hasattr(qp, "timings"):
        logger.debug(f"Query processing time: {qp.timings}")
    if hasattr(qp.tools, "timings"):
        logger.debug(f"Table Schema time: {qp.tools.timings}")

    # Return response
    response = DashboardQueryResponse(
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
