"""This module contains utility functions for the `question_answer` module."""

from .schemas import QuerySearchResult


def get_context_string_from_search_results(
    *, search_results: dict[int, QuerySearchResult]
) -> str:
    """Get the context string from the retrieved content.

    Parameters
    ----------
    search_results
        The search results retrieved from the search engine.

    Returns
    -------
    str
        The context string from the retrieved content.
    """

    context_list = []
    for key, result in search_results.items():
        if not isinstance(result, QuerySearchResult):
            result = QuerySearchResult(**result)
        context_list.append(f"{key}. {result.title}\n{result.text}")
    context_string = "\n\n".join(context_list)
    return context_string
