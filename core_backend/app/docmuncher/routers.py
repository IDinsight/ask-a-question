import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated, Union
from uuid import uuid4

import pandas as pd
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
from .schemas import (
    DocIngestionStatusPdf,
    DocIngestionStatusZip,
    DocStatusEnum,
    DocUploadResponsePdf,
    DocUploadResponseZip,
)

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
    zip_file_name = None
    if file.filename.endswith(".zip"):
        zip_file_name = file.filename
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
        await file.close()
    elif file.filename.endswith(".pdf"):
        file_content = await file.read()
        pdf_files = [(file.filename, file_content)]
        await file.close()

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for document ingestion.",
        )

    # 2.
    upload_id = str(uuid4())
    tasks: list[DocUploadResponsePdf] = []
    zip_created_datetime_utc = datetime.now(timezone.utc)

    for filename, content in pdf_files:
        bg_asession = AsyncSession(asession.bind)

        # 3.
        # Log task in redis
        redis = request.app.state.redis
        task_id = f"{JOB_KEY_PREFIX}{str(uuid4())}"
        task_status = DocUploadResponsePdf(
            upload_id=upload_id,
            user_id=calling_user_db.user_id,
            workspace_id=workspace_db.workspace_id,
            zip_file_name=zip_file_name,
            created_datetime_utc=datetime.now(timezone.utc),
            task_id=task_id,
            doc_name=filename,
            task_status=DocStatusEnum.not_started,
        )
        tasks.append(task_status)

        await redis.set(
            task_id, task_status.model_dump_json(), ex=REDIS_EXPIRATION_SECONDS
        )

        background_tasks.add_task(
            process_pdf_file,
            request=request,
            task_id=task_id,
            file_name=filename,
            content=content,
            workspace_id=workspace_db.workspace_id,
            asession=bg_asession,
        )

    if len(pdf_files) == 1:
        return tasks[0]
    else:
        return DocUploadResponseZip(
            upload_id=upload_id,
            user_id=calling_user_db.user_id,
            workspace_id=workspace_db.workspace_id,
            zip_file_name=file.filename,
            created_datetime_utc=zip_created_datetime_utc,
            tasks=tasks,
            zip_status=DocStatusEnum.not_started,
        )


@router.get("/status/user", response_model=bool)
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
    all_jobs_list = [json.loads(job.decode("utf-8")) for job in all_jobs]

    user_workspace_jobs = [
        job
        for job in all_jobs_list
        if job["user_id"] == calling_user_db.user_id
        and job["workspace_id"] == workspace_db.workspace_id
    ]

    if len(user_workspace_jobs) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No jobs found for this user in workspace {workspace_name}",
        )

    num_processes_running = sum(
        job["task_status"] == DocStatusEnum.in_progress for job in user_workspace_jobs
    )

    return True if num_processes_running > 0 else False


@router.get(
    "/status", response_model=list[Union[DocIngestionStatusPdf, DocIngestionStatusZip]]
)
async def get_all_jobs(
    request: Request,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[DocIngestionStatusPdf | DocIngestionStatusZip]:
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
    all_jobs_list = [json.loads(job.decode("utf-8")) for job in all_jobs]

    # Filter jobs for the workspace and user
    user_workspace_jobs = [
        job
        for job in all_jobs_list
        if job["user_id"] == calling_user_db.user_id
        and job["workspace_id"] == workspace_db.workspace_id
    ]

    if len(user_workspace_jobs) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No jobs found for this user in workspace {workspace_name}",
        )

    # Convert to pandas for easy grouping
    df = pd.DataFrame(user_workspace_jobs)
    df.created_datetime_utc = pd.to_datetime(df.created_datetime_utc)
    df.finished_datetime_utc = pd.to_datetime(df.finished_datetime_utc)
    df = df.sort_values(by="created_datetime_utc", ascending=False)
    df[pd.isna(df.error_trace)] = ""

    groups = df.groupby("upload_id")

    task_table: list[Union[DocIngestionStatusPdf, DocIngestionStatusZip]] = []
    for upload_id, group in groups:
        if len(group) == 1:
            task = group.to_dict(orient="records")[0]
            task_table.append(DocIngestionStatusPdf.model_validate(task))
        else:
            tasks = [
                DocIngestionStatusPdf.model_validate(task)
                for task in group.to_dict(orient="records")
            ]
            zip_task = dict(
                tasks=tasks,
                upload_id=upload_id,
                user_id=int(tasks[0].user_id),
                workspace_id=int(tasks[0].workspace_id),
                zip_file_name=tasks[0].zip_file_name,
                created_datetime_utc=tasks[0].created_datetime_utc,
                docs_total=len(tasks),
            )

            # Get the zip status and docs indexed numbers
            num_docs_success = sum(
                task.task_status == DocStatusEnum.success for task in tasks
            )
            num_docs_failed = sum(
                task.task_status == DocStatusEnum.failed for task in tasks
            )
            num_docs_in_progress = sum(
                task.task_status == DocStatusEnum.in_progress for task in tasks
            )

            zip_task["docs_indexed"] = len(tasks) - num_docs_in_progress
            zip_task["docs_failed"] = num_docs_failed

            if num_docs_in_progress > 0:
                zip_task["zip_status"] = DocStatusEnum.in_progress
                zip_task["finished_datetime_utc"] = None
                zip_task["error_trace"] = ""

            elif num_docs_success == len(tasks):
                zip_task["zip_status"] = DocStatusEnum.success
                zip_task["finished_datetime_utc"] = tasks[-1].finished_datetime_utc
                zip_task["error_trace"] = ""
            else:
                zip_task["zip_status"] = DocStatusEnum.failed
                zip_task["finished_datetime_utc"] = tasks[-1].finished_datetime_utc
                zip_task["error_trace"] = (
                    f"{num_docs_failed} documents failed to ingest."
                )

            task_table.append(DocIngestionStatusZip.model_validate(zip_task))
    return task_table
