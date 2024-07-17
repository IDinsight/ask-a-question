from datetime import datetime
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, StringConstraints


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation request
    """

    # Ensure len("*{title}*\n\n{text}") <= 1600
    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=2000)]
    content_tags: list = []
    content_metadata: dict = {}

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "content_title": "An example content title",
                    "content_text": "And an example content text!",
                },
            ]
        },
    )


class ContentRetrieve(ContentCreate):
    """
    Retrieved content class
    """

    content_id: int
    user_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    positive_votes: int
    negative_votes: int


class ContentUpdate(ContentCreate):
    """
    Pydantic model for content edit request
    """

    content_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "content_id": 1,
                    "content_title": "A new content title",
                    "content_text": "A new content text!",
                },
            ]
        },
    )


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
