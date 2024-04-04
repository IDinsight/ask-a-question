from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

AccessLevel = Literal["fullaccess", "readonly"]


class ContentTextCreate(BaseModel):
    """
    Pydantic model for content creation
    """

    # Ensure len("*{title}*\n\n{text}") <= 1600
    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=2000)]
    language_id: int = Field(default=1, description="Language ID")
    content_id: Optional[int] = Field(
        default=None,
        description="If adding or editing content text to an existing content"
        ", provide its ID",
    )

    content_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class ContentTextUpdate(ContentTextCreate):
    content_id: int


class ContentTextRetrieve(ContentTextCreate):
    """
    Pydantic model for content retrieval
    """

    content_text_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime


class ContentLanding(BaseModel):
    """
    Pydantic model
    for content summary
    """

    content_text_id: int
    content_id: int
    content_title: str
    content_text: str
    languages: list[str]
    created_datetime_utc: datetime
    updated_datetime_utc: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentUpdate(ContentTextCreate):
    """
    Pydantic model for content edit
    """

    content_id: int


class ContentDelete(BaseModel):
    """
    Pydantic model for content deletion
    """

    content_id: int
