"""This module contains FastAPI routers for document ingestion endpoints."""

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Request,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user, get_current_workspace_name
from app.core.database import get_async_session
from app.core.observability import setup_logger
from app.docmuncher import service
from app.docmuncher.schemas import (
    DocIngestionStatusZip,
    DocUploadResponsePdf,
    DocUploadResponseZip,
)
from app.users.models import UserDB

TAG_METADATA = {
    "name": "Document upload",
    "description": "_Requires user login._ Document management to create content",
}


router = APIRouter(prefix="/docmuncher", tags=[TAG_METADATA["name"]])
logger = setup_logger()


@router.post("/upload", response_model=DocUploadResponsePdf | DocUploadResponseZip)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> DocUploadResponsePdf | DocUploadResponseZip:
    """Upload pdf document to create content.

    The process is as follows:

    1. Parameters for the endpoint are checked first.
    2. Check if content / page limits are reached
    3. Create a copy of the file and asession
    4. Start a document ingestion job and return a job ID.

    Parameters
    ----------
    file
        The .pdf or .zip file to upload.
    calling_user_db
        The user object associated with the user that is creating the content.
    workspace_name
        The name of the workspace to create the content in.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    DocUploadResponsePdf | DocUploadResponseZip
        The response model for document upload.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        OR
        If the file is not a .pdf or .zip file.
    """
    logger.info("Document upload request received.")
    redis = request.app.state.redis

    # 1. Role and file-type checks happen before the file is read.
    workspace_db = await service.authorize_document_upload(
        asession=asession,
        calling_user_db=calling_user_db,
        filename=file.filename,
        workspace_name=workspace_name,
    )
    assert file.filename is not None  # Guaranteed by `authorize_document_upload`.
    file_content = await file.read()
    await file.close()

    # 2-3. Check quotas and log a job per PDF in redis.
    response, jobs = await service.create_ingestion_jobs(
        asession=asession,
        calling_user_db=calling_user_db,
        file_content=file_content,
        filename=file.filename,
        redis=redis,
        workspace_db=workspace_db,
    )

    # 4. Run each PDF ingestion job after the response is sent.
    for job in jobs:
        background_tasks.add_task(
            service.process_pdf_file,
            redis=redis,
            task_id=job.task_id,
            file_name=job.file_name,
            content=job.content,
            workspace_id=job.workspace_id,
            asession=job.asession,
        )

    return response


@router.get("/status/is_job_running", response_model=bool)
async def get_jobs_running_for_user(
    request: Request,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> bool:
    """Get the status of all jobs with certain status.

    Parameters:
    -----------
    request
        The request object from FastAPI.
    calling_user_db
        The user object associated with the user that is checking the status.
    workspace_name
        The name of the workspace to check the status in.
    asession
        The database session object.

    Returns:
    --------
    bool
        True if any jobs are running, False otherwise.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        OR
        If no jobs are not found.
    """
    return await service.is_job_running(
        asession=asession,
        calling_user_db=calling_user_db,
        redis=request.app.state.redis,
        workspace_name=workspace_name,
    )


@router.get("/status/data", response_model=list[DocIngestionStatusZip])
async def get_all_jobs(
    request: Request,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[DocIngestionStatusZip]:
    """Get the status of all jobs.

    Parameters:
    -----------
    request
        The request object from FastAPI.
    calling_user_db
        The user object associated with the user that is checking the status.
    workspace_name
        The name of the workspace to check the status in.
    asession
        The database session object.

    Returns:
    --------
    list[DocIngestionStatusPdf | DocIngestionStatusZip]
        The response from processing the PDF or .zip file.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        OR
        If no jobs are not found.
    """
    return await service.get_all_jobs(
        asession=asession,
        calling_user_db=calling_user_db,
        redis=request.app.state.redis,
        workspace_name=workspace_name,
    )
