import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..config import REDIS_DOC_INGEST_EXPIRY_TIME as REDIS_EXPIRATION_SECONDS
from ..database import get_async_session
from ..users.models import UserDB, user_has_required_role_in_workspace
from ..users.schemas import UserRoles
from ..utils import setup_logger
from ..workspaces.utils import (
    get_workspace_by_workspace_name,
)
from .dependencies import JOB_KEY_PREFIX, process_pdf_file
from .schemas import DocIngestionStatus, DocStatusEnum, DocUploadResponse

TAG_METADATA = {
    "name": "Document upload",
    "description": "_Requires user login._ Document management to create content",
}


router = APIRouter(prefix="/docmuncher", tags=[TAG_METADATA["name"]])
logger = setup_logger()


@router.post("/upload", response_model=list[DocUploadResponse])
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[DocUploadResponse]:
    """Upload pdf document to create content.

    The process is as follows:

    1. Parameters for the endpoint are checked first.
    2. Create a copy of the file and asession
    3. Start a document ingestion job and return a job ID.

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
    list[DocUploadResponse]
        The response model for document upload.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        If the document already exists.
    """
    logger.info("Document upload request received.")

    # 1.
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to ingest documents.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    pdf_files = []
    if file.filename.endswith(".zip"):
        zip_file_content = await file.read()
        with zipfile.ZipFile(BytesIO(zip_file_content)) as zip_file:
            pdf_files = [
                (f, zip_file.read(f)) for f in zip_file.namelist() if f.endswith(".pdf")
            ]
            if not pdf_files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The zip file does not contain any PDF files.",
                )
    elif file.filename.endswith(".pdf"):
        file_content = await file.read()
        pdf_files = [(file.filename, file_content)]
        file.close()

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for document ingestion.",
        )

    # 2.
    tasks: list[DocUploadResponse] = []
    for filename, content in pdf_files:
        bg_asession = AsyncSession(asession.bind)

        # 3.
        # Log task in redis
        redis = request.app.state.redis
        created_datetime_utc = datetime.now(timezone.utc)
        task_id = f"{JOB_KEY_PREFIX}{str(uuid4())}"
        task_status = DocUploadResponse(
            doc_name=filename,
            task_id=task_id,
            created_datetime_utc=created_datetime_utc,
            status=DocStatusEnum.not_started,
        )
        await redis.set(
            task_id, task_status.model_dump_json(), ex=REDIS_EXPIRATION_SECONDS
        )
        tasks.append(task_status)

        background_tasks.add_task(
            process_pdf_file,
            request=request,
            task_id=task_id,
            file_name=filename,
            content=BytesIO(content).getvalue(),
            workspace_id=workspace_db.workspace_id,
            asession=bg_asession,
        )

    return tasks


# TODO: Can deprecate if we don't use this endpoint
@router.get("/status/task/{task_id}", response_model=DocIngestionStatus)
async def get_doc_ingestion_status(
    request: Request,
    task_id: str,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> DocIngestionStatus:
    """Get document ingestion status.

    Parameters
    ----------
    task_id
        The ingestion job ID.
    calling_user_db
        The user object associated with the user that is checking the status.
    workspace_name
        The name of the workspace to check the status in.

    Returns
    -------
    DocUploadResponseStatus
        The response model for document upload status.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
    """
    # Check params
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to request ingestion status.",
        )

    # Query status response
    redis = request.app.state.redis
    job_status = await redis.get(task_id)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return DocIngestionStatus.model_validate(json.loads(job_status.decode("utf-8")))


@router.get("/status/{job_status}", response_model=dict)
async def get_jobs_by_status_type(
    request: Request,
    job_status: DocStatusEnum,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get the status of all jobs with certain status.

    Parameters:
    -----------
    request
        The request object from FastAPI.
    job_status
        The status of the job to get.
    calling_user_db
        The user object associated with the user that is checking the status.
    workspace_name
        The name of the workspace to check the status in.
    asession
        The database session object.

    Returns:
    --------
    list[DocIngestionStatus]
        The response from processing the PDF file.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        OR
        If no jobs are not found.
    """
    # Check params
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to request ingestion status.",
        )

    # Query status response
    redis = request.app.state.redis
    job_keys = await redis.keys(f"{JOB_KEY_PREFIX}*")
    if not job_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No jobs found",
        )

    all_jobs = await redis.mget(job_keys)
    filtered_jobs_list = [
        DocIngestionStatus.model_validate(json.loads(job.decode("utf-8")))
        for job in all_jobs
        if json.loads(job.decode("utf-8"))["status"] == job_status
    ]

    if not filtered_jobs_list:
        raise HTTPException(
            status_code=404,
            detail=f"No jobs of status {job_status} found",
        )

    return {
        "fraction_of_files": f"{len(filtered_jobs_list)}/{len(all_jobs)}",
        "jobs": sorted(
            filtered_jobs_list, key=lambda x: x.created_datetime_utc, reverse=True
        ),
    }


@router.get("/status", response_model=list[DocIngestionStatus])
async def get_all_jobs(
    request: Request,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[DocIngestionStatus]:
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
    list[DocIngestionStatus]
        The response from processing the PDF file.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create content in the workspace.
        OR
        If no jobs are not found.
    """
    # Check params
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to request ingestion status.",
        )

    # Query status response
    redis = request.app.state.redis
    job_keys = await redis.keys(f"{JOB_KEY_PREFIX}*")
    if not job_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No jobs found",
        )

    all_jobs = await redis.mget(job_keys)
    all_jobs_list = [
        DocIngestionStatus.model_validate(json.loads(job.decode("utf-8")))
        for job in all_jobs
    ]

    return sorted(all_jobs_list, key=lambda x: x.created_datetime_utc, reverse=True)
