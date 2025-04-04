from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocStatusEnum(str, Enum):
    """Enum for document status."""

    failed = "Failed"
    in_progress = "In progress"
    success = "Success"
    not_started = "Ingestion job created"


class DocUploadResponseBase(BaseModel):
    """Pydantic model for document upload response."""

    upload_id: str
    user_id: int
    workspace_id: int
    parent_file_name: Optional[str] = None
    created_datetime_utc: datetime


class DocUploadResponsePdf(DocUploadResponseBase):
    """Pydantic model for document upload response with pdf file."""

    task_id: str
    doc_name: str
    task_status: DocStatusEnum = DocStatusEnum.not_started


class DocUploadResponseZip(DocUploadResponseBase):
    """Pydantic model for document upload response with zip file."""

    tasks: list[DocUploadResponsePdf] = Field(default_factory=list)
    overall_status: DocStatusEnum = DocStatusEnum.not_started
    docs_total: int


class DocIngestionStatusBase(BaseModel):
    """Pydantic model for document ingestion status."""

    error_trace: Optional[str] = ""
    finished_datetime_utc: Optional[datetime] = None


class DocIngestionStatusPdf(DocUploadResponsePdf, DocIngestionStatusBase):
    """Pydantic model for document ingestion status."""

    pass


class DocIngestionStatusZip(DocUploadResponseBase, DocIngestionStatusBase):
    """Pydantic model for document ingestion status."""

    tasks: list[DocIngestionStatusPdf] = Field(default_factory=list)
    overall_status: DocStatusEnum = DocStatusEnum.not_started
    docs_indexed: int
    docs_failed: int
    docs_total: int
