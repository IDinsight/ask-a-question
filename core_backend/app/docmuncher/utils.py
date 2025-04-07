import re

from langchain_core.documents import Document


def is_image_only_card(chunk: Document) -> bool:
    """
    Determine if a card contains only image content.

    Parameters
    ----------
    chunk
        The document chunk to analyze.

    Returns
    -------
    bool
        True if the card only contains image content, False otherwise.
    """
    image_patterns = [
        r"!\[.*?\]\(.*?\)",
        r"<img.*?>",
    ]

    content = chunk.page_content.strip()

    for pattern in image_patterns:
        content = re.sub(pattern, "", content)

    return len(content.strip()) == 0 or content.isspace()


def is_table_in_card(chunk: Document) -> bool:
    """
    Determine if a card contains a table.

    Parameters
    ----------
    chunk
        The document chunk to analyze.

    Returns
    -------
    bool
        True if the card primarily contains a table, False otherwise.
    """
    content = chunk.page_content.strip()

    table_indicators = [
        r"\|.*\|.*\|",
        r"\+[-+]+\+",
        r"^\s*[-]+\s*\|\s*[-]+\s*$",
    ]

    for line in content.split("\n"):
        for pattern in table_indicators:
            if re.search(pattern, line):
                return True
    return False


def is_content_single_line(chunk: Document) -> bool:
    """
    Determine if a card contains only a single line of content.

    Parameters
    ----------
    chunk
        The document chunk to analyze.

    Returns
    -------
    bool
        True if the card contains only a single line of content, False otherwise.
    """
    content = chunk.page_content.strip()

    return len(content.split("\n")) == 1 and len(content.strip()) > 0
