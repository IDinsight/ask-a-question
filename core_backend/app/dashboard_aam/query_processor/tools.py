import re
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from aiocache import cached
from cachetools import TTLCache
from sqlalchemy import MetaData, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import CreateTable

from ..utils import track_time

_tools_instance = None


class DashboardSQLTools:
    """Tools to query the SQL database."""

    def __init__(self) -> None:
        """Initialize the SQLTools class."""
        self._max_sql_response_length = 20000
        self._response_too_long_message = "Sorry, SQL response was too long"
        self._schema_cache: TTLCache = TTLCache(maxsize=100, ttl=60 * 60 * 24)

    @staticmethod
    def handle_sql_response_length(func: Callable) -> Callable:
        """Decorator to handle the length of the SQL response."""

        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            """Wrapper"""
            response = await func(self, *args, **kwargs)
            if len(str(response)) > self._max_sql_response_length:
                return self._response_too_long_message
            return response

        return wrapper

    @staticmethod
    def _do_reflect(
        asession: AsyncSession,
        tables: Optional[List[str]] = None,
    ) -> Tuple[MetaData, List[str]]:
        """Reflect the tables."""
        metadata = MetaData()
        engine = asession.get_bind()
        inspector = inspect(engine)

        existing_table_names = []

        for table_name in inspector.get_table_names():
            if (tables is None or table_name in tables) and inspector.has_table(
                table_name
            ):
                existing_table_names.append(table_name)

        metadata.reflect(bind=engine, only=existing_table_names, views=True)
        return metadata, existing_table_names

    @track_time(create_class_attr="timings")
    @cached(ttl=60 * 60 * 24)
    @handle_sql_response_length
    async def _get_table_schema(
        self,
        table_list: List[str],
        asession: AsyncSession,
        user_id: int,
    ) -> dict[str, str]:
        """
        Queries the target SQL database and returns the schema of the tables.

        Args:
        - table_list (list[str]): The list of table names for which you
            want to get the schema.
        - asession (AsyncSession): The SQLAlchemy AsyncSession object.
        - user_id: user to filter for

        Returns:
        - dict[str, str]: The schema of all the relevant tables in the database.
        """
        return_schema = {table: "" for table in table_list}

        # Execute the reflection
        metadata, existing_tables = await asession.run_sync(
            lambda _: self._do_reflect(asession=asession, tables=table_list)
        )

        for table_name in existing_tables:
            table = metadata.tables.get(table_name)
            if table is not None:
                ddl_statement = str(
                    CreateTable(table).compile(bind=asession.get_bind())
                )
                return_schema[table.name] += f"\nTable: {table.name}\n{ddl_statement}\n"

                # Fetching the first three rows from the table
                if "user_id" in table.columns:
                    stmt = select(table).where(table.c.user_id == user_id).limit(3)
                else:
                    stmt = select(table).limit(3)

                first_n_rows_result = await asession.execute(stmt)
                first_n_rows = first_n_rows_result.mappings().all()
                first_n_rows_str = "\n".join(
                    ["\t".join(map(str, row.values())) for row in first_n_rows]
                )
                return_schema[table.name] += f"Sample rows:\n{first_n_rows_str}\n"

        return return_schema

    @track_time(create_class_attr="timings")
    @cached(ttl=60 * 60 * 24)
    @handle_sql_response_length
    async def get_tables_schema(
        self,
        table_list: List[str],
        asession: AsyncSession,
        user_id: int,
    ) -> str:
        """
        Queries the target SQL database and returns the schema of the tables.

        Args:
        - table_list (list[str]): The list of table names for which you
            want to get the schema.
        - asession (AsyncSession): The SQLAlchemy AsyncSession object.
        - user_id (int): The user id to filter for.

        Returns:
        - str: The schema of all the relevant tables in the database.
        """
        if user_id not in self._schema_cache:
            add_to_cache = await self._get_table_schema(
                table_list=table_list, asession=asession, user_id=user_id
            )
            self._schema_cache[user_id] = add_to_cache
        else:
            # Update cache with tables if not in cache
            tables_not_in_cache = [
                table
                for table in table_list
                if table not in self._schema_cache[user_id]
            ]
            if tables_not_in_cache:
                add_to_cache = await self._get_table_schema(
                    tables_not_in_cache, asession, user_id=user_id
                )
                self._schema_cache[user_id].update(add_to_cache)
        # Add the value for each table in table_list to return schema as a string append
        return_schema = "\n".join(
            [self._schema_cache[user_id][table] for table in table_list]
        )
        return return_schema

    @track_time(create_class_attr="timings")
    @cached(ttl=60 * 60 * 24)
    @handle_sql_response_length
    async def get_most_common_column_values(
        self,
        table_column_dict: Dict[str, List[str]],
        num_common_values: int,
        asession: AsyncSession,
        user_id: int,
    ) -> Dict[str, Dict]:
        """
        Queries the target SQL database and returns the top k (=num_common_values)
        most common values of the columns from respective tables.

        Args:
        - table_column_dict: A dictionary with table names as keys and a list of
            column names as values.
        - num_common_values (int): The number of most common values to return.

        Returns:
        - dict[str, dict]: A Dictionary with the top k common values for each table
            column combination which was asked for.
        """
        result: Dict[str, Dict] = {}

        tables_to_filter = await self.find_tables_with_user_id_column(
            tables=list(table_column_dict.keys()), asession=asession
        )

        for table, columns in table_column_dict.items():
            result[table] = {}
            if table in tables_to_filter:
                filter_statement = f"WHERE user_id = {user_id}"
            else:
                filter_statement = ""

            for column in columns:
                sql_response = await asession.execute(
                    text(
                        "\n".join(
                            [
                                f'SELECT {column} FROM "{table}"',
                                filter_statement,
                                f"""\
                                GROUP BY {column}
                                ORDER BY COUNT(*) DESC
                                LIMIT {num_common_values};
                                """,
                            ]
                        )
                    )
                )
                result[table][column] = sql_response.fetchall()

        return result

    @track_time(create_class_attr="timings")
    @cached(ttl=60 * 60 * 24)
    @handle_sql_response_length
    async def run_sql(
        self,
        sql_query: str,
        asession: AsyncSession,
        tables: List[str],
        user_id: int,
    ) -> Sequence[Any]:
        """
        Executes the SQL query on the target SQL database.

        Args:
        - sql_query (str): The SQL query to execute.
        - asession (AsyncSession): The SQLAlchemy AsyncSession object.

        Returns:
        - List: The result of the SQL query.
        """
        tables_to_filter = await self.find_tables_with_user_id_column(
            asession=asession, tables=tables
        )
        user_filtered_sql_query = self.create_user_filtered_query_with_cte(
            raw_sql=sql_query,
            user_id=user_id,
            tables_to_filter=tables_to_filter,
        )
        quoted_sql_query = self.quote_table_names(tables, user_filtered_sql_query)
        sql_response = await asession.execute(text(quoted_sql_query))

        return sql_response.fetchall()

    async def find_tables_with_user_id_column(
        self,
        asession: AsyncSession,
        tables: Optional[List[str]] = None,
    ) -> List[str]:
        """Find tables with user ID column."""
        metadata, table_names = await asession.run_sync(
            lambda _: self._do_reflect(asession=asession, tables=tables)
        )

        tables_with_user_id = []

        for table_name in table_names:
            table = metadata.tables[table_name]
            if "user_id" in table.columns:
                tables_with_user_id.append(table_name)

        return tables_with_user_id

    @staticmethod
    def create_user_filtered_query_with_cte(
        raw_sql: str, user_id: int, tables_to_filter: List[str]
    ) -> str:
        """Ensure tables are filtered by user_id before running any queries, if user_id
        column exists. Prepends common table expression (CTE, WITH clause) that filters
        relevant tables, and replaces table names in the raw SQL with the filtered
        tables.
        """
        # Define the common table expressions (CTEs) for tables that need filtering
        ctes = []
        for table in tables_to_filter:
            cte = (
                f'"{table}_filtered" AS (SELECT * FROM "{table}"'
                f"WHERE user_id = {user_id})"
            )
            ctes.append(cte)

        # Join the CTEs into a single string
        if len(ctes) > 0:
            cte_string = "WITH " + ", ".join(ctes)

            # Replace the table names in the raw SQL with their corresponding CTEs
            for table in tables_to_filter:
                raw_sql = re.sub(rf"\b{table}\b", f'"{table}_filtered"', raw_sql)

            # Combine the CTE string with the modified SQL query
            filtered_sql = f"{cte_string} {raw_sql}"

            return filtered_sql
        return raw_sql

    @staticmethod
    def quote_table_names(tables: List[str], raw_sql: str) -> str:
        """Quote table names as they can contain `-`."""
        for table in tables:
            raw_sql = re.sub(rf'\b^"{table}^"\b', f'"{table}"', raw_sql)
        return raw_sql


def get_tools() -> DashboardSQLTools:
    """Return the SQLTools instance."""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = DashboardSQLTools()
    return _tools_instance
