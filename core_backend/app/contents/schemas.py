from datetime import datetime
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, StringConstraints


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation
    """

    # Ensure len("*{title}*\n\n{text}") <= 1600
    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=2000)]
    content_tags: list = []
    content_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class ContentRetrieve(ContentCreate):
    """
    Pydantic model for content retrieval
    """

    content_id: int
    user_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    positive_votes: int
    negative_votes: int


class ContentUpdate(ContentCreate):
    """
    Pydantic model for content edit
    """

    content_id: int


class ContentDelete(BaseModel):
    """
    Pydantic model for content deletiom
    """

    content_id: int


class CustomError(BaseModel):
    """
    Pydantic model for custom error
    """

    type: str
    description: str


class CustomErrorList(BaseModel):
    """
    Pydantic model for list of custom errors
    """

    errors: List[CustomError]
