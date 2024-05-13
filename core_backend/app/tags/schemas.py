from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

AccessLevel = Literal["fullaccess", "readonly"]


class TagCreate(BaseModel):
    """
    Pydantic model for content creation
    """

    tag_name: Annotated[str, StringConstraints(max_length=50)]

    model_config = ConfigDict(from_attributes=True)


class TagRetrieve(TagCreate):
    """
    Pydantic model for tag retrieval
    """

    tag_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime


class TagUpdate(TagCreate):
    """
    Pydantic model for tag edit
    """

    content_id: int


class TagDelete(BaseModel):
    """
    Pydantic model for tag deletion
    """

    content_id: int
