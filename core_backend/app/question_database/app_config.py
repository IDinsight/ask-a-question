import os

from pydantic import Field, create_model
from pydantic_settings import BaseSettings


class DefaultSettings(BaseSettings):
    """
    Default settings of env variables for the application
    """

    LOG_LEVEL: str = "INFO"
    DOMAIN: str = "localhost"
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    GUARDRAILS_LLM_MODEL: str = "gpt-4o"
    REQUEST_TIMEOUT: str = "10"
    LLM_MODEL_MAX_CHAR: str = "120"
    BACKEND_ROOT_PATH: str = ""


class DBSettings(DefaultSettings):
    """
    Settings for the databases
    """

    WHICH_DB: str = ""
    METRIC_DB_PATH: str = ""
    METRIC_DB_TYPE: str = ""
    METRIC_DB_SYNC_API: str = ""
    METRIC_DB_ASYNC_API: str = ""
    SYSTEM_MESSAGE: str = ""
    METRIC_DB_TABLE_DESCRIPTION: str = ""
    METRIC_DB_COLUMN_DESCRIPTION: str = ""
    NUM_FOR_TOP_K_COMMON_VALUES: int = 10
    METRIC_DB_USER: str = ""
    METRIC_DB_PASSWORD: str = ""
    METRIC_DB_HOST: str = ""
    METRIC_DB_PORT: str = ""
    METRIC_DB: str = ""


settings = DefaultSettings()

# Make a dictionary with bearer tokens as keys and db names as values
bearer_tokens_dict = {
    v: k.split("_AUTH_BEARER_TOKEN")[0]
    for k, v in os.environ.items()
    if k.endswith("_AUTH_BEARER_TOKEN")
}

# Dynamically create a pydantic class for each db name
db_specific_settings = {}
for db_name in bearer_tokens_dict.values():
    class_name = f"{db_name}Settings"
    db_settings_dict = {
        "WHICH_DB": (
            str,
            Field(f"metric_{db_name.lower()}", validation_alias=f"{db_name}_WHICH_DB"),
        ),
        "METRIC_DB_PATH": (
            str,
            Field(
                "",
                validation_alias=f"{db_name}_DB_PATH",
            ),
        ),
        "METRIC_DB_TYPE": (str, Field("sqlite", validation_alias=f"{db_name}_DB_TYPE")),
        "METRIC_DB_SYNC_API": (
            str,
            Field("", validation_alias=f"{db_name}_DB_SYNC_API"),
        ),
        "METRIC_DB_ASYNC_API": (
            str,
            Field("aiosqlite", validation_alias=f"{db_name}_DB_ASYNC_API"),
        ),
        "SYSTEM_MESSAGE": (
            str,
            Field("", validation_alias=f"{db_name}_SYSTEM_MESSAGE"),
        ),
        "METRIC_DB_TABLE_DESCRIPTION": (
            str,
            Field("", validation_alias=f"{db_name}_DB_TABLE_DESCRIPTION"),
        ),
        "METRIC_DB_COLUMN_DESCRIPTION": (
            str,
            Field("", validation_alias=f"{db_name}_DB_COLUMN_DESCRIPTION"),
        ),
        "METRIC_DB_USER": (str, Field("", validation_alias=f"{db_name}_DB_USER")),
        "METRIC_DB_PASSWORD": (
            str,
            Field("", validation_alias=f"{db_name}_DB_PASSWORD"),
        ),
        "METRIC_DB_HOST": (str, Field("", validation_alias=f"{db_name}_DB_HOST")),
        "METRIC_DB_PORT": (str, Field("", validation_alias=f"{db_name}_DB_PORT")),
        "METRIC_DB": (str, Field("", validation_alias=f"{db_name}_DB")),
        "NUM_COMMON_VALUES": (
            int,
            Field(10, validation_alias=f"{db_name}_NUM_COMMON_VALUES"),
        ),
    }

    globals()[class_name] = create_model(
        class_name, __base__=DBSettings, **db_settings_dict
    )
    db_specific_settings[f"metric_{db_name.lower()}"] = globals()[class_name]()
