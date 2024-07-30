from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import UserQueryBase
from ..utils import _ask_llm_json, track_time
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
        query: UserQueryBase,
        asession: AsyncSession,
        which_db: str,
        llm: str,
        guardrails_llm: str,
        sys_message: str,
        db_description: str,
        column_description: str,
        num_common_values: int,
    ) -> None:
        """Initialize the QueryProcessor class."""
        self.query = query
        self.asession = asession
        self.which_db = which_db
        self.tools: SQLTools = get_tools()
        self.temperature = 0.1
        self.llm = llm
        self.system_message = sys_message
        self.table_description = db_description
        self.column_description = column_description
        self.num_common_values = num_common_values
        self.guardrails: LLMGuardRails = LLMGuardRails(
            guardrails_llm, self.system_message
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

        query_language_llm_response = await _ask_llm_json(
            prompt, system_message, llm=self.llm, temperature=self.temperature
        )
        self.query_language = query_language_llm_response["answer"]["language"]
        self.query_script = query_language_llm_response["answer"]["script"]

        self.cost += float(query_language_llm_response["cost"])

    @track_time(create_class_attr="timings")
    async def _get_best_tables_from_llm(self) -> None:
        """
        The function asks the LLM model to identify the best
        tables to answer a question.
        """
        prompt = create_best_tables_prompt(self.query, self.table_description)
        best_tables_llm_response = await _ask_llm_json(
            prompt, self.system_message, llm=self.llm, temperature=self.temperature
        )

        self.best_tables = best_tables_llm_response["answer"]["response_sources"]
        self.cost += float(best_tables_llm_response["cost"])
        self.best_tables_prompt = prompt

    @track_time(create_class_attr="timings")
    async def _get_best_columns_from_llm(self) -> None:
        """
        The function asks the LLM model to identify the best columns
        to answer a question.
        """
        self.relevant_schemas = await self.tools.get_tables_schema(
            self.best_tables, self.asession, which_db=self.which_db
        )
        prompt = create_best_columns_prompt(
            self.query,
            self.relevant_schemas,
            columns_description=self.column_description,
        )
        best_columns_llm_response = await _ask_llm_json(
            prompt, self.system_message, llm=self.llm, temperature=self.temperature
        )

        self.best_columns = best_columns_llm_response["answer"]
        self.cost += float(best_columns_llm_response["cost"])
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
        sql_query_llm_response = await _ask_llm_json(
            prompt, self.system_message, llm=self.llm, temperature=self.temperature
        )

        self.sql_query = sql_query_llm_response["answer"]["sql"]
        self.cost += float(sql_query_llm_response["cost"])
        self.sql_generating_prompt = prompt

    @track_time(create_class_attr="timings")
    async def _get_final_answer_from_llm(self) -> None:
        """
        The function asks the LLM model to generate the final
        answer to the user's question.
        """
        sql_result = await self.tools.run_sql(self.sql_query, self.asession)
        prompt = create_final_answer_prompt(
            self.query,
            self.sql_query,
            sql_result,
            self.query_language,
            self.query_script,
        )
        final_answer_llm_response = await _ask_llm_json(
            prompt, self.system_message, llm=self.llm, temperature=self.temperature
        )

        self.final_answer = final_answer_llm_response["answer"]["answer"]
        self.cost += float(final_answer_llm_response["cost"])
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
