from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class DocStatusEnum(str, Enum):
    """Enum for document status."""

    failed = "Failed"
    in_progress = "In progress"
    success = "Success"
    not_started = "Ingestion job created"


class DocUploadResponse(BaseModel):
    """Pydantic model for document upload response."""

    doc_name: str
    task_id: str
    created_datetime_utc: datetime
    status: DocStatusEnum


class DocIngestionStatus(DocUploadResponse):
    """Pydantic model for document ingestion status."""

    error_trace: Optional[str] = ""
    finished_datetime_utc: Optional[datetime] = None
