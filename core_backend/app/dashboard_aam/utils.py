import json
import logging
import time
from functools import wraps
from logging import Logger
from typing import Any, Callable

from aiocache import cached
from litellm import acompletion, completion_cost

from .app_config import settings


def get_log_level_from_str(log_level_str: str = settings.LOG_LEVEL) -> int:
    """
    Get log level from string
    """
    log_level_dict = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }

    return log_level_dict.get(log_level_str.upper(), logging.INFO)


def setup_logger(
    name: str = __name__, log_level: int = get_log_level_from_str()
) -> Logger:
    """
    Setup logger for the application
    """
    logger = logging.getLogger(name)

    # If the logger already has handlers,
    # assume it was already configured and return it.
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(filename)20s%(lineno)4s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


llm_call_logger = setup_logger("LLM_call")


@cached(ttl=60 * 60 * 24)
async def _ask_llm_json(
    prompt: str,
    system_message: str,
    llm: str = settings.LLM_MODEL,
    temperature: float = 0.1,
) -> dict:
    """
    A generic function to ask the LLM model a question and return
    the response in JSON format.

    Args:
        prompt (str): The prompt to ask the LLM model
        system_message (str): The system message to ask the LLM model
    """
    llm_call_logger.debug(f"LLM input: 'model': {llm}, 'messages': {prompt}")
    response = await acompletion(
        model=llm,
        temperature=temperature,
        messages=[
            {"content": system_message, "role": "system"},
            {"content": prompt, "role": "user"},
        ],
        response_format={"type": "json_object"},
    )

    cost = completion_cost(response)

    result = {
        "answer": json.loads(response.choices[0].message.content),
        "cost": cost,
    }

    return result


def track_time(create_class_attr: str) -> Callable:
    """
    Decorator to add time tracking within classes.

    It adds an attribute "create_attr" to the class instance
    if it does not exist. Else, it appends the time taken
    by the function to the attribute.
    """

    def decorator(func: Callable) -> Callable:
        """Decorator"""

        @wraps(func)
        async def wrapper(self: Any, *args: str, **kwargs: str) -> Any:
            """Wrapper"""
            start_time = time.time()
            result = await func(self, *args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            if hasattr(self, create_class_attr):
                getattr(self, create_class_attr)[func.__name__] = elapsed_time
            else:
                setattr(self, create_class_attr, {func.__name__: elapsed_time})
            return result

        return wrapper

    return decorator
