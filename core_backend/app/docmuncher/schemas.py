from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class DocStatusEnum(str, Enum):
    """Enum for document status."""

    failed = "failed"
    in_progress = "in_progress"
    success = "success"
    not_started = "not_started"


class DocUploadResponse(BaseModel):
    """Pydantic model for document upload response."""

    doc_name: str
    ingestion_job_id: str
    ingestion_message: Optional[str] = ""
    created_datetime_utc: datetime
    finished_datetime_utc: Optional[datetime] = None
    status: DocStatusEnum
