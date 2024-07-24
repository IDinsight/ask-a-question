from copy import deepcopy
from datetime import datetime
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, StringConstraints


class ContentCreate(BaseModel):
    """
    Pydantic model for content creation request
    """

    content_title: Annotated[str, StringConstraints(max_length=150)]
    content_text: Annotated[str, StringConstraints(max_length=2000)]
    content_tags: list = []
    content_metadata: dict = {}
    is_archived: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "content_title": "An example content title",
                    "content_text": "And an example content text!",
                    "content_tags": [1, 4],
                    "content_metadata": {"example": "optional metadata"},
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
    is_archived: bool

    model_config = deepcopy(ContentCreate.model_config)
    model_config["json_schema_extra"]["examples"][0].update(
        {
            "content_id": 1,
            "user_id": 1,
            "created_datetime_utc": "2024-01-01T00:00:00",
            "updated_datetime_utc": "2024-01-01T00:00:00",
            "positive_votes": 1,
            "negative_votes": 0,
        }
    )


class ContentUpdate(ContentCreate):
    """
    Pydantic model for content edit request
    """

    content_id: int

    model_config = deepcopy(ContentCreate.model_config)
    model_config["json_schema_extra"]["examples"][0].update(
        {
            "content_id": 1,
        }
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
