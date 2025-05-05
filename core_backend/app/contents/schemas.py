"""This module contains Pydantic models for content endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ContentCreate(BaseModel):
    """Pydantic model for content creation request."""

    content_metadata: dict = Field(default_factory=dict)
    content_tags: list = Field(default_factory=list)
    content_text: str = Field(
        # max_length=2000,
        examples=["This is an example content."],
    )
    content_title: str = Field(
        # max_length=150,
        examples=["Example Content Title"],
    )
    is_archived: bool = False
    related_contents_id: Optional[list[int]] = []
    is_validated: bool = True

    model_config = ConfigDict(from_attributes=True)


class ContentDelete(BaseModel):
    """Pydantic model for content deletion."""

    content_id: int


class ContentRetrieve(ContentCreate):
    """Pydantic model for content retrieval response."""

    content_id: int
    display_number: int
    created_datetime_utc: datetime
    is_archived: bool
    negative_votes: int
    positive_votes: int

    updated_datetime_utc: datetime
    workspace_id: int

    model_config = ConfigDict(from_attributes=True)


class ContentUpdate(ContentCreate):
    """Pydantic model for content edit request."""

    content_id: int

    model_config = ConfigDict(from_attributes=True)


class CustomError(BaseModel):
    """Pydantic model for custom error."""

    description: str
    type: str


class CustomErrorList(BaseModel):
    """Pydantic model for list of custom errors."""

    errors: list[CustomError]
