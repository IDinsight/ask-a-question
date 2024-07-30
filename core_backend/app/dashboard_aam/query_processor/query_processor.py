import json

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import LITELLM_MODEL_DASHBOARD
from ...llm_call.utils import _ask_llm_async
from ..schemas import DashboardQueryBase
from ..utils import track_time
from .guardrails.guardrails import LLMGuardRails
from .query_processing_prompts import (
    create_best_columns_prompt,
    create_best_tables_prompt,
    create_final_answer_prompt,
    create_sql_generating_prompt,
    get_query_language_prompt,
)
from .tools import SQLTools, get_tools


class LLMQueryProcessor:
    """Processes the user query and returns the final answer."""

    def __init__(
        self,
        query: DashboardQueryBase,
        asession: AsyncSession,
        user: str,
        sys_message: str,
        db_description: str,
        column_description: str,
        num_common_values: int,
        llm: str = LITELLM_MODEL_DASHBOARD,
        guardrails_llm: str = LITELLM_MODEL_DASHBOARD,
    ) -> None:
        """Initialize the QueryProcessor class."""
        self.query = query
        self.asession = asession
        self.user = user
        self.tools: SQLTools = get_tools()
        self.temperature = 0.1
        self.llm = llm
        self.system_message = sys_message
        self.table_description = db_description
        self.column_description = column_description
        self.num_common_values = num_common_values
        self.guardrails: LLMGuardRails = LLMGuardRails(
            sys_message=self.system_message,
            gurdrails_llm=guardrails_llm,
        )
        self.cost = 0.0
        self.language_prompt = ""
        self.query_language = ""
        self.script = ""
        self.best_tables: str = ""
        self.best_columns: str = ""
        self.sql_query: str = ""
        self.final_answer: str = ""
        self.relevant_schemas: str = ""
        self.best_tables_prompt: str = ""
        self.best_columns_prompt: str = ""
        self.sql_generating_prompt: str = ""
        self.final_answer_prompt: str = ""

    @track_time(create_class_attr="timings")
    async def _get_query_language_from_llm(self) -> None:
        """
        The function asks the LLM model to identify the language
        of the user's query.
        """
        system_message, prompt = get_query_language_prompt(self.query["query_text"])
        self.language_prompt = prompt

        response = await _ask_llm_async(
            question=prompt,
            prompt=system_message,
            litellm_model=self.llm,
            temperature=self.temperature,
            json=True,
        )

        result = json.loads(response)
        self.query_language = result["language"]
        self.query_script = result["script"]

    @track_time(create_class_attr="timings")
    async def _get_best_tables_from_llm(self) -> None:
        """
        The function asks the LLM model to identify the best
        tables to answer a question.
        """
        prompt = create_best_tables_prompt(self.query, self.table_description)
        response = await _ask_llm_async(
            question=prompt,
            prompt=prompt,
            litellm_model=self.llm,
            temperature=self.temperature,
            json=True,
        )

        best_tables = json.loads(response)

        self.best_tables = best_tables["response_sources"]
        self.best_tables_prompt = prompt

    @track_time(create_class_attr="timings")
    async def _get_best_columns_from_llm(self) -> None:
        """
        The function asks the LLM model to identify the best columns
        to answer a question.
        """
        self.relevant_schemas = await self.tools.get_tables_schema(
            table_list=self.best_tables, asession=self.asession, user=self.user
        )
        prompt = create_best_columns_prompt(
            self.query,
            self.relevant_schemas,
            columns_description=self.column_description,
        )
        response = await _ask_llm_async(
            question=prompt,
            prompt=self.system_message,
            litellm_model=self.llm,
            temperature=self.temperature,
            json=True,
        )
        best_columns = json.loads(response)
        self.best_columns = best_columns
        self.best_columns_prompt = prompt

    @track_time(create_class_attr="timings")
    async def _get_sql_query_from_llm(self) -> None:
        """
        The function asks the LLM model to generate a SQL query to
        answer the user's question.
        """
        self.top_k_common_values = await self.tools.get_common_column_values(
            self.best_columns, self.num_common_values, self.asession
        )
        prompt = create_sql_generating_prompt(
            self.query,
            self.relevant_schemas,
            self.top_k_common_values,
            self.column_description,
            self.num_common_values,
        )
        response = await _ask_llm_async(
            question=prompt,
            prompt=self.system_message,
            litellm_model=self.llm,
            temperature=self.temperature,
            json=True,
        )
        sql_query_llm_response = json.loads(response)

        self.sql_query = sql_query_llm_response["sql"]
        self.sql_generating_prompt = prompt

    @track_time(create_class_attr="timings")
    async def _get_final_answer_from_llm(self) -> None:
        """
        The function asks the LLM model to generate the final
        answer to the user's question.
        """
        sql_result = await self.tools.run_sql(
            self.sql_query, self.asession
        )  # TODO: add where user_id = self.user
        prompt = create_final_answer_prompt(
            self.query,
            self.sql_query,
            sql_result,
            self.query_language,
            self.query_script,
        )
        response = await _ask_llm_async(
            prompt,
            self.system_message,
            litellm_model=self.llm,
            temperature=self.temperature,
            json=True,
        )

        final_answer_llm_response = json.loads(response)
        self.final_answer = final_answer_llm_response["answer"]
        self.final_answer_prompt = prompt

    @track_time(create_class_attr="timings")
    async def process_query(self) -> None:
        """
        The function processes the user query and returns the final answer.
        """
        # Get query language
        await self._get_query_language_from_llm()

        # Check query safety
        await self.guardrails.check_safety(
            self.query["query_text"], self.query_language, self.query_script
        )
        if self.guardrails.safe is False:
            self.final_answer = self.guardrails.safety_response
            return None

        # Check answer relevance
        await self.guardrails.check_relevance(
            self.query["query_text"],
            self.query_language,
            self.query_script,
            self.table_description,
        )

        if self.guardrails.relevant is False:
            self.final_answer = self.guardrails.relevance_response
            return None

        await self._get_best_tables_from_llm()
        await self._get_best_columns_from_llm()
        await self._get_sql_query_from_llm()
        await self._get_final_answer_from_llm()
