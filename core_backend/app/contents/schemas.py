from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation request
    """

    content_title: str = Field(
        max_length=150,
        examples=["Example Content Title"],
    )
    content_text: str = Field(
        max_length=2000,
        examples=["This is an example content."],
    )
    content_tags: list = Field(default=[])
    content_metadata: dict = Field(default={})
    is_archived: bool = False

    model_config = ConfigDict(
        from_attributes=True,
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
    is_archived: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


class ContentUpdate(ContentCreate):
    """
    Pydantic model for content edit request
    """

    content_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class ContentDelete(BaseModel):
    """
    Pydantic model for content deletion
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
