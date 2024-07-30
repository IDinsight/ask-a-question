import time
from functools import wraps
from typing import Any, Callable


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
