import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    validator,
)


class LanguageBase(BaseModel):
    """
    Pydantic model for language
    """

    language_name: str
    is_default: bool
    model_config = ConfigDict(from_attributes=True)

    @validator("language_name")
    def language_name_must_be_valid(cls, value: str) -> str:
        # Regex pattern allows letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\-' ]+$", value):
            raise ValueError("Invalid characters in language name.")
        return value


class LanguageRetrieve(LanguageBase):
    """
    Pydantic model for language retrieval
    """

    language_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    model_config = ConfigDict(from_attributes=True)
