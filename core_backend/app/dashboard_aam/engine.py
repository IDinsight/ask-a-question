from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from .app_config import db_specific_settings

# global so we don't create more than one engine per process
# outside of being best practice, this is needed so we can properly pool
# connections and not create a new pool on every request
_ENGINES: dict[str, dict[str, Engine | AsyncEngine | None]] = {
    key: {"sync": None, "async": None} for key in db_specific_settings.keys()
}


# TODO: Add support for other databases
def build_connection_string(**kwargs: str) -> str:
    """
    Return a connection string for async engine for the given database.

    Args:
        db_type (str, optional): The type of database.
            Options are "postgresql" or "sqlite".
        kwargs: The keyword arguments for the database connection.
            if db_type is "postgresql", the following keyword arguments are reqd:
                db_api (str): The async database API.
                user (str): The username for the database.
                password (str): The password for the database.
                host (str): The host for the database.
                port (str): The port for the database.
                db (str): The name of the database.
            if db_type is "sqlite", the following keyword arguments are required:
                db_api (str): The async database API.
                db_path (str): relative path to the database file.
    """
    db_type = kwargs["db_type"]
    if db_type == "postgresql":
        db_string = "{db_type}+{db_api}://{user}:{password}@{host}:{port}/{db}"
    elif db_type == "sqlite":
        if kwargs["db_api"] == "":
            db_string = "{db_type}:///{db_path}"
        else:
            db_string = "{db_type}+{db_api}:///{db_path}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
    return db_string.format_map(kwargs)


def get_sqlalchemy_async_engine(
    which_db: str = "typebot", **kwargs: str
) -> AsyncEngine:
    """
    Return a SQLAlchemy async engine.

    Args:
        which_db (str): Which database to get engine for, "typebot" or
            "metric_<db_name>". Default is "typebot".
        **kwargs: The keyword arguments for the database connection.
    """
    global _ENGINES

    engine = _ENGINES[which_db]["async"]
    if engine is None:
        connection_string = build_connection_string(**kwargs)
        print(f"Connection string: {connection_string}")
        _ENGINES[which_db]["async"] = create_async_engine(
            connection_string, poolclass=NullPool
        )
    return _ENGINES[which_db]["async"]
