from typing import Dict

from .schemas import QuerySearchResult


def convert_search_results_to_schema(
    results: Mapping[int, tuple]
) -> Dict[int, QuerySearchResult]:
    """Converts retrieval results to schema."""
    return {
        i: QuerySearchResult(
            title=value[0],
            text=value[1],
            id=value[2],
            score=value[3],
        )
        for i, value in results.items()
    }


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
        context_list.append(f"{int(i)+1}. {result.title}\n{result.text}")
    context_string = "\n\n".join(context_list)
    return context_string
