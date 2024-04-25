from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, validator

from ..llm_call.llm_prompts import IdentifiedLanguage

AccessLevel = Literal["fullaccess", "readonly"]


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation
    """

    # Ensure len("*{title}*\n\n{text}") <= 1600
    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=2000)]
    content_language: str = "ENGLISH"
    content_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)

    @validator("content_language")
    def validate_language(cls, v: str) -> str:
        """
        Validator for language
        """

        if v not in IdentifiedLanguage.get_supported_languages():
            raise ValueError(f"Language {v} is not supported")

        return v


class ContentRetrieve(ContentCreate):
    """
    Pydantic model for content retrieval
    """

    content_id: int
    user_id: str
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
