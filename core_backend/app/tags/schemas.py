from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class TagCreate(BaseModel):
    """
    Pydantic model for content creation
    """

    tag_name: Annotated[str, StringConstraints(max_length=50)]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "tag_name": "example-tag",
                },
                {
                    "tag_name": "ABC",
                },
            ]
        },
    )


class TagRetrieve(TagCreate):
    """
    Pydantic model for tag retrieval
    """

    tag_id: int
    user_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_id": 1,
                    "tag_name": "example-tag",
                    "user_id": 1,
                    "created_datetime_utc": "2024-01-01T00:00:00",
                    "updated_datetime_utc": "2024-01-01T00:00:00",
                },
                {
                    "tag_id": 2,
                    "tag_name": "ABC",
                    "user_id": 1,
                    "created_datetime_utc": "2024-01-01T00:00:00",
                    "updated_datetime_utc": "2024-01-01T00:00:00",
                },
            ]
        },
    )
