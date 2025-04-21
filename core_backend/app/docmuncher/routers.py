import json
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated
from uuid import uuid4

import numpy as np
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
from PyPDF2 import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..config import (
    CHECK_CONTENT_LIMIT,
    PAGES_TO_CARDS_CONVERSION,
    REDIS_DOC_INGEST_EXPIRY_TIME,
)
from ..contents.routers import (
    ExceedsContentQuotaError,
    _check_content_quota_availability,
)
from ..database import get_async_session
from ..users.models import UserDB, user_has_required_role_in_workspace
from ..users.schemas import UserRoles
from ..utils import setup_logger
from ..workspaces.utils import get_workspace_by_workspace_name
from .dependencies import JOB_KEY_PREFIX, process_pdf_file
from .schemas import (
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
    num_pages = 0
    parent_file_name = None
    if file.filename.endswith(".zip"):
        parent_file_name = file.filename
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
            num_pages = sum(
                len(PdfReader(BytesIO(content)).pages) for _, content in pdf_files
            )
        await file.close()
    elif file.filename.endswith(".pdf"):
        file_content = await file.read()
        pdf_files = [(file.filename, file_content)]
        num_pages = len(PdfReader(BytesIO(file_content)).pages)
        await file.close()

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for document ingestion.",
        )

    # 3.
    # Get temporary log of expected contents to be created by running jobs
    temp_docmuncher_contents = await redis.get(
        f"{workspace_db.workspace_id}_docmuncher_contents"
    )
    if not temp_docmuncher_contents:
        temp_docmuncher_contents = 0
    else:
        temp_docmuncher_contents = int(temp_docmuncher_contents.decode("utf-8"))
    num_expected_contents = (
        num_pages * PAGES_TO_CARDS_CONVERSION + temp_docmuncher_contents
    )

    if CHECK_CONTENT_LIMIT:
        if workspace_db.content_quota and (
            num_pages > workspace_db.content_quota / PAGES_TO_CARDS_CONVERSION
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Document ingestion exceeds page quota:\n\
                    There are {num_pages} pages in your upload, but only\
                    {workspace_db.content_quota / PAGES_TO_CARDS_CONVERSION}\
                    pages are allowed.",
            )
        try:
            await _check_content_quota_availability(
                asession=asession,
                n_contents_to_add=num_expected_contents,
                workspace_id=workspace_db.workspace_id,
            )
        except ExceedsContentQuotaError as e:
            match = re.search(r"existing (\d+) in the database", str(e))
            existing_contents = 0
            if match:
                existing_contents = int(match.group(1))
            pages_left = max(
                0,
                workspace_db.content_quota
                - temp_docmuncher_contents
                - existing_contents,
            )
            pages_left = np.floor(pages_left / PAGES_TO_CARDS_CONVERSION).astype(int)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Document ingestion could exceed content quota:\n\
                    There are {num_pages} pages in your upload, but only\
                    {pages_left} more pages are allowed.",
            ) from e

    upload_id = str(uuid4())
    tasks: list[DocUploadResponsePdf] = []
    zip_created_datetime_utc = datetime.now(timezone.utc)

    for filename, content in pdf_files:
        bg_asession = AsyncSession(asession.bind)
        # 3.
        # Log task in redis
        task_id = f"{JOB_KEY_PREFIX}{str(uuid4())}"
        task_status = DocUploadResponsePdf(
            upload_id=upload_id,
            user_id=calling_user_db.user_id,
            workspace_id=workspace_db.workspace_id,
            parent_file_name=parent_file_name,
            created_datetime_utc=datetime.now(timezone.utc),
            task_id=task_id,
            doc_name=filename,
            task_status=DocStatusEnum.not_started,
        )
        tasks.append(task_status)

        await redis.set(
            task_id, task_status.model_dump_json(), ex=REDIS_DOC_INGEST_EXPIRY_TIME
        )
        # Update expected contents from running jobs
        await redis.set(
            f"{workspace_db.workspace_id}_docmuncher_contents", num_expected_contents
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

    # 4.
    if len(pdf_files) == 1:
        return tasks[0]
    else:
        return DocUploadResponseZip(
            upload_id=upload_id,
            user_id=calling_user_db.user_id,
            workspace_id=workspace_db.workspace_id,
            parent_file_name=parent_file_name,
            created_datetime_utc=zip_created_datetime_utc,
            tasks=tasks,
            overall_status=DocStatusEnum.not_started,
            docs_total=len(pdf_files),
        )


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
        job for job in all_jobs_list if job["workspace_id"] == workspace_db.workspace_id
    ]

    if len(user_workspace_jobs) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No jobs found in workspace {workspace_name}",
        )

    num_processes_running = sum(
        job["task_status"] == DocStatusEnum.in_progress for job in user_workspace_jobs
    )

    return True if num_processes_running > 0 else False


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
        job for job in all_jobs_list if job["workspace_id"] == workspace_db.workspace_id
    ]

    if len(user_workspace_jobs) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No jobs found in workspace {workspace_name}",
        )

    # Group jobs by upload id
    upload_ids = np.unique(
        [str(job["upload_id"]) for job in user_workspace_jobs]
    ).tolist()

    task_table: list[DocIngestionStatusZip] = []
    for upload_id in upload_ids:
        group = [job for job in user_workspace_jobs if job["upload_id"] == upload_id]
        tasks = sorted(group, key=lambda x: x["created_datetime_utc"])

        if len(group) == 1:
            task = tasks[0]

            zip_task = dict(
                tasks=[task],
                upload_id=upload_id,
                user_id=int(task["user_id"]),
                workspace_id=int(task["workspace_id"]),
                parent_file_name=task["doc_name"],
                created_datetime_utc=task["created_datetime_utc"],
                overall_status=task["task_status"],
                finished_datetime_utc=task["finished_datetime_utc"],
                error_trace=task["error_trace"],
                docs_total=1,
                docs_indexed=(
                    1
                    if task["task_status"]
                    not in [DocStatusEnum.in_progress, DocStatusEnum.not_started]
                    else 0
                ),
                docs_failed=1 if task["task_status"] == DocStatusEnum.failed else 0,
            )

            task_table.append(DocIngestionStatusZip.model_validate(zip_task))
        else:
            zip_task = dict(
                tasks=tasks,
                upload_id=upload_id,
                user_id=int(tasks[0]["user_id"]),
                workspace_id=int(tasks[0]["workspace_id"]),
                parent_file_name=tasks[0]["parent_file_name"],
                created_datetime_utc=tasks[0]["created_datetime_utc"],
                docs_total=len(group),
            )

            # Get the zip status and docs indexed numbers
            num_docs_success = sum(
                task["task_status"] == DocStatusEnum.success for task in tasks
            )
            num_docs_failed = sum(
                task["task_status"] == DocStatusEnum.failed for task in tasks
            )
            num_docs_in_progress = sum(
                task["task_status"] == DocStatusEnum.in_progress for task in tasks
            )
            num_docs_not_started = sum(
                task["task_status"] == DocStatusEnum.not_started for task in tasks
            )

            zip_task["docs_indexed"] = (
                len(tasks)
                - num_docs_in_progress
                - num_docs_not_started
                - num_docs_failed
            )
            zip_task["docs_failed"] = num_docs_failed

            if num_docs_failed > 0:
                failed_files = [
                    task["doc_name"]
                    for task in tasks
                    if task["task_status"] == DocStatusEnum.failed
                ]
                failed_files_preview = ", ".join(failed_files[:3]) + (
                    "..." if len(failed_files) > 3 else ""
                )
                zip_task["overall_status"] = DocStatusEnum.failed
                zip_task["finished_datetime_utc"] = tasks[-1].get(
                    "finished_datetime_utc", None
                )
                zip_task["error_trace"] = (
                    f"{num_docs_failed} documents failed to ingest. "
                    f"Failed files: {failed_files_preview}"
                )
            elif num_docs_in_progress > 0:
                zip_task["overall_status"] = DocStatusEnum.in_progress
                zip_task["finished_datetime_utc"] = None
                zip_task["error_trace"] = ""
            elif num_docs_success == len(tasks):
                zip_task["overall_status"] = DocStatusEnum.success
                zip_task["finished_datetime_utc"] = tasks[-1].get(
                    "finished_datetime_utc", None
                )
                zip_task["error_trace"] = ""
            else:
                zip_task["overall_status"] = DocStatusEnum.not_started
                zip_task["finished_datetime_utc"] = None
                zip_task["error_trace"] = ""

            task_table.append(DocIngestionStatusZip.model_validate(zip_task))
    return task_table
