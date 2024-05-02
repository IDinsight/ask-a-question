from typing import Dict, Mapping

from .schemas import QuerySearchResult


def convert_search_results_to_schema(
    results: Mapping[int, tuple]
) -> Dict[int, QuerySearchResult]:
    """Converts retrieval results to schema."""
    return {
        i: QuerySearchResult(
            retrieved_title=value[0],
            retrieved_text=value[1],
            retrieved_content_id=value[2],
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
        context_list.append(f"{i+1}. {result.retrieved_title}\n{result.retrieved_text}")
    context_string = "\n\n".join(context_list)
    return context_string
