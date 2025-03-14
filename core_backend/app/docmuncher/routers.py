from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..database import get_async_session
from ..tags.models import (
    is_tag_name_unique,
    save_tag_to_db,
)
from ..tags.schemas import TagCreate
from ..users.models import UserDB, user_has_required_role_in_workspace
from ..users.schemas import UserRoles
from ..utils import setup_logger
from ..workspaces.utils import (
    get_workspace_by_workspace_name,
)
from .dependencies import process_pdf_file
from .schemas import DocStatusEnum, DocUploadResponse

TAG_METADATA = {
    "name": "Document upload",
    "description": "_Requires user login._ Document management to create content",
}

router = APIRouter(prefix="/docmuncher", tags=[TAG_METADATA["name"]])
logger = setup_logger()


@router.post("/upload", response_model=DocUploadResponse)
async def upload_document(
    request: Request,
    # background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> DocUploadResponse:
    """Upload document to create content.

    The process is as follows:

    1. Parameters for the endpoint are checked first.
    2. Add a content tag for the uploaded document.
    3, Start a document ingestion job and return a job ID.

    Parameters
    ----------
    file
        The file to upload (.pdf or .zip).
    calling_user_db
        The user object associated with the user that is creating the content.
    workspace_name
        The name of the workspace to create the content in.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    DocUploadResponse
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

    # 2.
    tag = TagCreate(tag_name=file.filename.upper())
    if not await is_tag_name_unique(
        asession=asession, tag_name=tag.tag_name, workspace_id=workspace_db.workspace_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag name `{tag.tag_name}` already exists",
        )
    tag_db = await save_tag_to_db(
        asession=asession, tag=tag, workspace_id=workspace_db.workspace_id
    )

    # 3.
    # Log task in redis
    redis = request.app.state.redis
    created_datetime_utc = datetime.now(timezone.utc)
    task_id = hash(file.filename + str(created_datetime_utc))
    task_status = DocUploadResponse(
        doc_name=file.filename,
        ingestion_job_id=task_id,
        created_datetime_utc=created_datetime_utc,
        status=DocStatusEnum.not_started,
    )
    await redis.set(task_id, task_status.model_dump_json())

    # Start background task
    await process_pdf_file(
        request=request,
        task_id=task_id,
        file=file,
        tag_id=tag_db.tag_id,
        workspace_id=workspace_db.workspace_id,
        asession=asession,
    )
    # background_tasks.add_task(
    #     process_pdf_file,
    #     request=request,
    #     task_id=task_id,
    #     file=file,
    #     tag_id=tag_db.tag_id,
    #     workspace_id=workspace_db.workspace_id,
    #     asession=asession,
    # )

    return task_status


@router.get("/status", response_model=DocUploadResponse)
async def get_doc_ingestion_status(
    request: Request,
    ingestion_job_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> DocUploadResponse:
    """Get document ingestion status.

    Parameters
    ----------
    ingestion_job_id
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
            detail="User does not have the required role to ingest documents.",
        )

    # Query status response
    redis = request.app.state.redis
    doc_status = redis.get(ingestion_job_id)
    return DocUploadResponse.model_validate(doc_status)
