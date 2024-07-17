from typing import Dict

from .schemas import QuerySearchResult


def get_context_string_from_retrieved_contents(
    content_response: Dict[int, QuerySearchResult]
) -> str:
    """
    Get the context string from the retrieved content
    """
    context_list = []
    for i, result in content_response.items():
        if not isinstance(result, QuerySearchResult):
            result = QuerySearchResult(**result)
        context_list.append(
            f"{int(i)+1}. {result.retrieved_title}\n{result.retrieved_text}"
        )
    context_string = "\n\n".join(context_list)
    return context_string
