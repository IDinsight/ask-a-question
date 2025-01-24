"""This module contains Pydantic models for tag endpoints."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class TagCreate(BaseModel):
    """Pydantic model for tag creation."""

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
    """Pydantic model for tag retrieval."""

    created_datetime_utc: datetime
    tag_id: int
    workspace_id: int
    updated_datetime_utc: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tag_id": 1,
                    "tag_name": "example-tag",
                    "workspace_id": 1,
                    "created_datetime_utc": "2024-01-01T00:00:00",
                    "updated_datetime_utc": "2024-01-01T00:00:00",
                },
                {
                    "tag_id": 2,
                    "tag_name": "ABC",
                    "workspace_id": 1,
                    "created_datetime_utc": "2024-01-01T00:00:00",
                    "updated_datetime_utc": "2024-01-01T00:00:00",
                },
            ]
        },
    )
