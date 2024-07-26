from datetime import datetime
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation request
    """

    content_title: Annotated[str, StringConstraints(max_length=150)] = Field(
        examples=["Example Content Title"],
    )
    content_text: Annotated[str, StringConstraints(max_length=2000)] = Field(
        examples=["This is an example content."]
    )
    content_tags: list = Field(default=[], examples=[[1, 4]])
    content_metadata: dict = Field(default={}, examples=[{"key": "optional_value"}])
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
