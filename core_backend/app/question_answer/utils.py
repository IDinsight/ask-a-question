from typing import Dict

from .schemas import QuerySearchResult


def get_context_string_from_search_results(
    search_results: Dict[int, QuerySearchResult]
) -> str:
    """
    Get the context string from the retrieved content
    """
    context_list = []
    for key, result in search_results.items():
        if not isinstance(result, QuerySearchResult):
            result = QuerySearchResult(**result)
        context_list.append(f"{key}. {result.title}\n{result.text}")
    context_string = "\n\n".join(context_list)
    return context_string
