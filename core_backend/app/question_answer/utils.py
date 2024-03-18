from typing import Dict, Mapping
from uuid import uuid4

from .schemas import UserQuerySearchResult


def generate_secret_key() -> str:
    """
    Generate a secret key for the user query
    """
    return uuid4().hex


def convert_search_results_to_schema(
    results: Mapping[int, tuple]
) -> Dict[int, UserQuerySearchResult]:
    return {
        i: UserQuerySearchResult(
            retrieved_title=value[0],
            retrieved_text=value[1],
            score=value[2],
        )
        for i, value in results.items()
    }
