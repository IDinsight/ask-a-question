"""Business logic for docmuncher: turning PDFs into content cards."""

from __future__ import annotations

import json
import os
import re
import zipfile
from datetime import datetime, timezone
from http import HTTPStatus
from io import BytesIO
from typing import Dict, NamedTuple
from uuid import uuid4

import numpy as np
import redis.asyncio as aioredis
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from mistralai import DocumentURLChunk, Mistral
from PyPDF2 import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.repository import save_content_to_db
from app.contents.schemas import ContentCreate
from app.contents.service import (
    ExceedsContentQuotaError,
    _check_content_quota_availability,
)
from app.core.config import (
    CHECK_CONTENT_LIMIT,
    LITELLM_MODEL_DOCMUNCHER_PARAPHRASE_TABLE,
    LITELLM_MODEL_DOCMUNCHER_SINGLE_LINE,
    LITELLM_MODEL_DOCMUNCHER_TITLE,
    PAGES_TO_CARDS_CONVERSION,
    REDIS_DOC_INGEST_EXPIRY_TIME,
)
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.core.observability import setup_logger
from app.core.utils import ask_llm_async
from app.docmuncher.schemas import (
    DocIngestionStatusPdf,
    DocIngestionStatusZip,
    DocStatusEnum,
    DocUploadResponsePdf,
    DocUploadResponseZip,
)
from app.tags.repository import is_tag_name_unique, save_tag_to_db
from app.tags.schemas import TagCreate
from app.users.models import UserDB
from app.users.repository import user_has_required_role_in_workspace
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import get_workspace_by_workspace_name

# ---- from docmuncher/prompts
# ---- Generate summaries for DocMuncher Cards -----
SYSTEM_DOCMUNCHER_TITLE = """
You are an excellent linguist.
Look at the content and metadata that the user provides and generate an
appropriate title of 8 WORDS OR LESS that captures the essence of the content.
The title should be in the SAME language as the content.
"""


USER_DOCMUNCHER_TITLE = """
Please generate a title for the following content:\n
Metadata: {meta} \n
Content: {content}"
"""


SYSTEM_DOCMUNCHER_TABLE = """
You are an excellent data analyst. You need to help non-technical people
understand technical information.
Look at the table and metadata that the user provides and PARAPHRASE the
information in the table so a layman can understand it.
I will share this information directly with the user, so just give me the
PARAPHRASED information in the SAME language as the content, without
conversational references to the table.
"""


USER_DOCMUNCHER_TABLE = """
Please paraphrase the following table:\n
Metadata: {meta} \n
Content: {content}"
"""


SYSTEM_SINGLE_LINE_CARD = """
You are an excellent linguist. Look at the content that the user provides and
decide whether the content is a caption / subtitle OR a a paragraph of text
containing meaningful information.
If the content is a caption / subtitle, please respond with True.
Otherwise, respond with False.
"""


USER_SINGLE_LINE_CARD = """
Please decide whether the following content is a caption / subtitle OR a
paragraph of text containing meaningful information:\n
Content: {content}"
"""


# ---- from docmuncher/service
logger = setup_logger()
MISTRAL_CLIENT = None
JOB_KEY_PREFIX = "docmuncher_job_"


class PdfIngestionJob(NamedTuple):
    """A PDF ingestion job to be run as a background task via `process_pdf_file`."""

    task_id: str
    file_name: str
    content: bytes
    workspace_id: int
    asession: AsyncSession


def _format_error(e: Exception) -> str:
    """Format an exception for logs and the job's `error_trace`.

    Domain errors are formatted as `"<status_code>: <detail>"`, which matches how
    `HTTPException` used to stringify, so the stored `error_trace` is unchanged.

    Parameters
    ----------
    e
        The exception to format.

    Returns
    -------
    str
        The formatted error message.
    """

    if isinstance(e, AppError):
        return f"{e.status_code}: {e.detail}"
    return str(e)


def get_mistral_client() -> Mistral:
    """
    Get a Mistral client instance.
    """
    global MISTRAL_CLIENT
    if MISTRAL_CLIENT is None:
        MISTRAL_CLIENT = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    return MISTRAL_CLIENT


async def create_tag_per_file(
    filename: str, workspace_id: int, asession: AsyncSession
) -> list:
    """
    Create a tag for a file.

    Parameters
    ----------
    filename
        The name of the file to create a tag for.
    workspace_id
        The workspace ID to save the tag in.
    asession
        The database session object.

    Returns
    -------
    list
        The content tags.
    """
    if not filename:
        raise BadRequestError("Filename is required")

    tag = TagCreate(tag_name=filename.upper()[:50])
    if not await is_tag_name_unique(
        asession=asession, tag_name=tag.tag_name, workspace_id=workspace_id
    ):
        raise BadRequestError(f"Tag name `{tag.tag_name}` already exists")
    tag_db = await save_tag_to_db(
        asession=asession, tag=tag, workspace_id=workspace_id, commmit=False
    )

    return [tag_db]


def convert_pages_to_markdown(file_name: str, content: bytes) -> dict:
    """
    Convert a PDF file to dictionary of markdown text.

    Parameters
    ----------
    file_name
        The PDF filename to convert.
    content
        The content of the PDF file.

    Returns
    -------
    dict
        The content of the PDF file in markdown formatted text.
    InternalServerError
        If the conversion fails.
    """
    client = get_mistral_client()

    try:
        uploaded_file = client.files.upload(
            file={
                "file_name": file_name,
                "content": content,
            },
            purpose="ocr",
        )

        signed_url = client.files.get_signed_url(file_id=uploaded_file.id)

        pdf_response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model="mistral-ocr-latest",
            include_image_base64=False,
        )

        markdown_text = json.loads(pdf_response.model_dump_json())
    except Exception as e:
        raise InternalServerError(f"Failed to convert PDF to markdown: {e}") from e
    return markdown_text


def chunk_markdown_text_by_headers(markdown_text: dict) -> dict:
    """
    Chunk markdown text by headers.

    Parameters
    ----------
    markdown_text
        The markdown text to chunk.

    Returns
    -------
    dict
        The chunked markdown text.
    InternalServerError
        If the chunking fails.
    """
    # Define header types
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    md_header_splits: Dict[int, Dict] = {}

    try:
        # First split markdown by headers
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]

        for i, page in enumerate(markdown_text["pages"]):
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on, return_each_line=True
            )
            header_splits = markdown_splitter.split_text(page["markdown"])
            md_header_splits[i] = {}
            for j, header_split in enumerate(header_splits):
                header_split.metadata.update(
                    {
                        "page": i,
                        "chunk": j,
                    }
                )
                # Update headers in metadata
                for header in headers_to_split_on:
                    if (
                        (header[1] not in header_split.metadata.keys())
                        and (len(md_header_splits[i]) > 0)
                        and (header[1] in md_header_splits[i][j - 1].metadata.keys())
                    ):
                        header_split.metadata[header[1]] = md_header_splits[i][
                            j - 1
                        ].metadata[header[1]]
                md_header_splits[i][j] = header_split

    except Exception as e:
        raise InternalServerError(f"Failed to chunk markdown text: {e}") from e
    return md_header_splits


async def merge_chunks_for_continuity(md_header_splits: dict) -> list:
    """
    Merge cards for continuity across pages.

    Parameters
    ----------
    md_header_splits
        The markdown header splits to merge.

    Returns
    -------
    list
        The merged markdown header splits.
    InternalServerError
        If the merging fails.
    """
    try:
        merged_chunks = []
        md_chunks_list = list(md_header_splits.values())

        for i, page in enumerate(md_chunks_list):
            for j, chunk in enumerate(page.values()):
                is_last_chunk = j == len(page) - 1
                is_last_page = i == len(md_chunks_list) - 1

                if is_last_chunk and not is_last_page:
                    next_chunk = md_chunks_list[i + 1][0]
                    combined_content = chunk.page_content + next_chunk.page_content
                    combined_metadata = {**chunk.metadata, **next_chunk.metadata}
                    combined_metadata["page"] = chunk.metadata["page"]
                    combined_metadata["chunk"] = chunk.metadata["chunk"]

                    combined_metadata["title"] = "Placeholder title"
                    merged_chunks.append(
                        Document(
                            metadata=combined_metadata, page_content=combined_content
                        )
                    )
                else:
                    merged_chunks.append(chunk)
    except Exception as e:
        raise InternalServerError(f"Failed to merge cards for continuity: {e}") from e
    return merged_chunks


async def deal_with_incorrectly_formatted_cards(merged_chunks: list) -> list:
    """
    Deal with incorrectly formatted cards.

    Parameters
    ----------
    merged_chunks
        The merged markdown header splits to process.

    Returns
    -------
    list
        The processed merged markdown header splits.
    Exception
        If the processing fails.
    """
    final_merged_chunks = []
    for chunk in merged_chunks:
        is_single_line = await is_content_single_line(chunk)
        is_image_card = is_image_only_card(chunk)
        if is_image_card or is_single_line:
            continue

        if is_table_in_card(chunk):
            chunk.page_content = await ask_llm_async(
                json_=False,
                litellm_model=LITELLM_MODEL_DOCMUNCHER_PARAPHRASE_TABLE,
                metadata=chunk.metadata,
                system_message=SYSTEM_DOCMUNCHER_TABLE,
                user_message=USER_DOCMUNCHER_TABLE.format(
                    meta=json.dumps(chunk.metadata), content=chunk.page_content
                ),
            )
        chunk.metadata["title"] = await ask_llm_async(
            json_=False,
            litellm_model=LITELLM_MODEL_DOCMUNCHER_TITLE,
            metadata=chunk.metadata,
            system_message=SYSTEM_DOCMUNCHER_TITLE,
            user_message=USER_DOCMUNCHER_TITLE.format(
                meta=json.dumps(chunk.metadata), content=chunk.page_content
            ),
        )
        chunk.metadata["title"] = chunk.metadata["title"].strip('"')
        final_merged_chunks.append(chunk)
    return final_merged_chunks


async def convert_markdown_chunks_to_cards(
    merged_chunks: list,
    content_tags: list,
    workspace_id: int,
    asession: AsyncSession,
) -> dict:
    """
    Convert markdown chunks to cards.

    Parameters
    ----------
    merged_chunks
        The markdown header splits to convert to cards.
    content_tags:
        The tags (associated with the filename) to save the cards with.
    workspace_id
        The workspace ID to save the cards in.
    asession
        The database session object.

    Returns
    ------
    dict
        The response from saving
    InternalServerError
        If the conversion fails.
    """

    try:
        for header_split in merged_chunks:
            metadata = header_split.metadata
            title = metadata.pop("title")

            card = ContentCreate(
                content_text=header_split.page_content,
                content_title=title,
                content_metadata=metadata,
                content_tags=content_tags,
                is_validated=False,
            )
            await save_content_to_db(
                asession=asession,
                content=card,
                exclude_archived=True,
                workspace_id=workspace_id,
                commit=False,
            )

    except Exception as e:
        # TODO: this is a dumb way to handle errors in card creation
        raise InternalServerError(f"Failed to process PDF file: {e}") from e
    return {"detail": "Cards saved successfully"}


async def process_pdf_file(
    redis: aioredis.Redis,
    task_id: str,
    file_name: str,
    content: bytes,
    workspace_id: int,
    asession: AsyncSession,
) -> DocIngestionStatusPdf:
    """
    Process a PDF file.

    Parameters
    ----------
    redis
        The Redis client (from `app.state.redis`) holding the job status.
    task_id
        The Redis key of the job to update.
    file_name
        The PDF filename to process.
    content
        The content of the PDF file.
    content_tags
        The tag (associated with the filename) to save the cards with.
    workspace_id
        The workspace ID to save the cards in.
    asession
        The database session object.

    Returns
    -------
    dict
        The response from processing the PDF file.
    NotFoundError
        If the job is not found in Redis.
    """
    # --- Update redis state operations ---
    # Get the job status
    job_status = await redis.get(task_id)
    if not job_status:
        raise NotFoundError("Job not found")

    job_status_dict = json.loads(job_status.decode("utf-8"))
    job_status_pydantic = DocIngestionStatusPdf(
        **job_status_dict,
        error_trace="",
        finished_datetime_utc=None,
    )

    try:
        # Acquire a lock for this file
        lock = f"lock:{file_name}"
        acquired_lock = await redis.set(
            lock, "1", nx=True, ex=REDIS_DOC_INGEST_EXPIRY_TIME
        )

        if not acquired_lock:
            raise AppError(
                f"File `{file_name}` has already been converted.",
                status_code=HTTPStatus.LOCKED,
            )

        job_status_pydantic.task_status = DocStatusEnum.in_progress
        await redis.set(task_id, job_status_pydantic.model_dump_json())

        # Process PDF file
        markdown_text = convert_pages_to_markdown(file_name=file_name, content=content)
        md_header_splits = chunk_markdown_text_by_headers(markdown_text)
        merged_chunks = await merge_chunks_for_continuity(md_header_splits)
        final_merged_chunks = await deal_with_incorrectly_formatted_cards(
            merged_chunks=merged_chunks
        )

        # Create the tags and save the merged cards to the database
        content_tags = await create_tag_per_file(
            filename=file_name, workspace_id=workspace_id, asession=asession
        )
        await convert_markdown_chunks_to_cards(
            merged_chunks=final_merged_chunks,
            content_tags=content_tags,
            workspace_id=workspace_id,
            asession=asession,
        )

        # Commit the changes to the database
        await asession.commit()

        # Update the job status
        job_status_pydantic.task_status = DocStatusEnum.success
        job_status_pydantic.finished_datetime_utc = datetime.now(timezone.utc)

    except Exception as e:
        error_message = _format_error(e)
        logger.error(f"Error processing file {file_name}: {error_message}")
        await asession.rollback()

        job_status_pydantic.task_status = DocStatusEnum.failed
        job_status_pydantic.error_trace = error_message
        job_status_pydantic.finished_datetime_utc = datetime.now(timezone.utc)

        # Release the lock
        await redis.delete(lock)

    finally:
        await redis.set(task_id, job_status_pydantic.model_dump_json())

        temp_docmuncher_contents = await redis.get(
            f"{workspace_id}_docmuncher_contents"
        )
        num_pages = len(PdfReader(BytesIO(content)).pages)

        # Update expected contents since task has finished
        await redis.set(
            f"{workspace_id}_docmuncher_contents",
            max(
                0, int(temp_docmuncher_contents) - num_pages * PAGES_TO_CARDS_CONVERSION
            ),
        )
        await asession.close()

    return job_status_pydantic


def is_image_only_card(chunk: Document) -> bool:
    """
    Determine if a card contains only image content.

    Parameters
    ----------
    chunk
        The document chunk to analyze.

    Returns
    -------
    bool
        True if the card only contains image content, False otherwise.
    """
    image_patterns = [
        r"!\[.*?\]\(.*?\)",
        r"<img.*?>",
    ]

    content = chunk.page_content.strip()

    for pattern in image_patterns:
        content = re.sub(pattern, "", content)

    return len(content.strip()) == 0 or content.isspace()


def is_table_in_card(chunk: Document) -> bool:
    """
    Determine if a card contains a table.

    Parameters
    ----------
    chunk
        The document chunk to analyze.

    Returns
    -------
    bool
        True if the card primarily contains a table, False otherwise.
    """
    content = chunk.page_content.strip()

    table_indicators = [
        r"\|.*\|.*\|",
        r"\+[-+]+\+",
        r"^\s*[-]+\s*\|\s*[-]+\s*$",
    ]

    for line in content.split("\n"):
        for pattern in table_indicators:
            if re.search(pattern, line):
                return True
    return False


async def is_content_single_line(chunk: Document) -> bool:
    """
    Determine if a card contains only a single line of content.

    Parameters
    ----------
    chunk
        The document chunk to analyze.

    Returns
    -------
    bool
        True if the card contains only a single line of content, False otherwise.
    """
    content = chunk.page_content.strip()
    if len(content.split("\n")) > 1:
        return False
    is_single_line = await ask_llm_async(
        json_=False,
        litellm_model=LITELLM_MODEL_DOCMUNCHER_SINGLE_LINE,
        metadata=chunk.metadata,
        system_message=SYSTEM_SINGLE_LINE_CARD,
        user_message=USER_SINGLE_LINE_CARD.format(content=content),
    )
    return is_single_line == "True"


async def _get_workspace_as_admin(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    forbidden_detail: str,
    workspace_name: str,
) -> WorkspaceDB:
    """Fetch the workspace and ensure the calling user is an admin in it.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user making the request.
    forbidden_detail
        The error detail to return if the user is not an admin in the workspace.
    workspace_name
        The name of the workspace.

    Returns
    -------
    WorkspaceDB
        The workspace object.

    Raises
    ------
    ForbiddenError
        If the user does not have the admin role in the workspace.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise ForbiddenError(forbidden_detail)

    return workspace_db


async def authorize_document_upload(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    filename: str | None,
    workspace_name: str,
) -> WorkspaceDB:
    """Check that the user may ingest documents and that the upload is supported.

    Runs before the uploaded file is read, so unsupported uploads are rejected
    without touching the file contents.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is uploading the document.
    filename
        The name of the uploaded file.
    workspace_name
        The name of the workspace to create the content in.

    Returns
    -------
    WorkspaceDB
        The workspace to ingest the document into.

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to ingest documents.
    BadRequestError
        If the filename is missing or the file is not a .pdf or .zip file.
    """

    workspace_db = await _get_workspace_as_admin(
        asession=asession,
        calling_user_db=calling_user_db,
        forbidden_detail="User does not have the required role to ingest documents.",
        workspace_name=workspace_name,
    )

    if not filename:
        raise BadRequestError("Filename is required")

    if not (filename.endswith(".zip") or filename.endswith(".pdf")):
        raise BadRequestError("Only PDF files are supported for document ingestion.")

    return workspace_db


async def create_ingestion_jobs(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    file_content: bytes,
    filename: str,
    redis: aioredis.Redis,
    workspace_db: WorkspaceDB,
) -> tuple[DocUploadResponsePdf | DocUploadResponseZip, list[PdfIngestionJob]]:
    """Check quotas and register one ingestion job per PDF in Redis.

    The process is as follows:

    1. Extract the PDF(s) from the upload and count their pages.
    2. Check that the expected number of new contents fits the workspace quota,
       counting contents expected from jobs that are still running.
    3. Log each job in Redis and return the jobs for the caller to schedule.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections. Each job
        gets its own session bound to the same engine.
    calling_user_db
        The user object associated with the user that is uploading the document.
    file_content
        The raw bytes of the uploaded .pdf or .zip file.
    filename
        The name of the uploaded file (already validated to end in .pdf or .zip).
    redis
        The Redis client used to track ingestion jobs.
    workspace_db
        The workspace to ingest the document into.

    Returns
    -------
    tuple[DocUploadResponsePdf | DocUploadResponseZip, list[PdfIngestionJob]]
        The upload response and the jobs to run as background tasks.

    Raises
    ------
    BadRequestError
        If the zip file does not contain any PDF files.
    ForbiddenError
        If the upload would exceed the workspace page or content quota.
    """

    # 1.
    pdf_files = []
    num_pages = 0
    parent_file_name = None
    if filename.endswith(".zip"):
        parent_file_name = filename
        with zipfile.ZipFile(BytesIO(file_content)) as zip_file:
            pdf_files = [
                (f, zip_file.read(f)) for f in zip_file.namelist() if f.endswith(".pdf")
            ]
            if not pdf_files:
                raise BadRequestError("The zip file does not contain any PDF files.")
            num_pages = sum(
                len(PdfReader(BytesIO(content)).pages) for _, content in pdf_files
            )
    else:
        pdf_files = [(filename, file_content)]
        num_pages = len(PdfReader(BytesIO(file_content)).pages)

    # 2.
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
            # NB: the embedded runs of spaces are part of the existing API error
            # message (they came from line continuations) and are kept verbatim.
            raise ForbiddenError(
                f"Document ingestion exceeds page quota:\n"
                f"                    There are {num_pages} pages in your upload, "
                f"but only                    "
                f"{workspace_db.content_quota / PAGES_TO_CARDS_CONVERSION}"
                f"                    pages are allowed."
            )
        try:
            await _check_content_quota_availability(
                asession=asession,
                n_contents_to_add=num_expected_contents,
                workspace_id=workspace_db.workspace_id,
            )
        except ExceedsContentQuotaError as e:
            # Recover the existing content count from the quota error message.
            match = re.search(r"existing (\d+) in the database", str(e))
            existing_contents = 0
            if match:
                existing_contents = int(match.group(1))
            assert isinstance(workspace_db.content_quota, int)
            pages_left = max(
                0,
                workspace_db.content_quota
                - temp_docmuncher_contents
                - existing_contents,
            )
            pages_left = np.floor(pages_left / PAGES_TO_CARDS_CONVERSION).astype(int)
            raise ForbiddenError(
                f"Document ingestion could exceed content quota:\n"
                f"                    There are {num_pages} pages in your upload, "
                f"but only                    "
                f"{pages_left} more pages are allowed."
            ) from e

    # 3.
    upload_id = str(uuid4())
    tasks: list[DocUploadResponsePdf] = []
    jobs: list[PdfIngestionJob] = []
    zip_created_datetime_utc = datetime.now(timezone.utc)

    for pdf_name, content in pdf_files:
        # Each background job needs its own session; the request's session is
        # closed once the response is sent.
        bg_asession = AsyncSession(asession.bind)
        # Log task in redis
        task_id = f"{JOB_KEY_PREFIX}{str(uuid4())}"
        task_status = DocUploadResponsePdf(
            upload_id=upload_id,
            user_id=calling_user_db.user_id,
            workspace_id=workspace_db.workspace_id,
            parent_file_name=parent_file_name,
            created_datetime_utc=datetime.now(timezone.utc),
            task_id=task_id,
            doc_name=pdf_name,
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

        jobs.append(
            PdfIngestionJob(
                task_id=task_id,
                file_name=pdf_name,
                content=content,
                workspace_id=workspace_db.workspace_id,
                asession=bg_asession,
            )
        )

    if len(pdf_files) == 1:
        return tasks[0], jobs
    return (
        DocUploadResponseZip(
            upload_id=upload_id,
            user_id=calling_user_db.user_id,
            workspace_id=workspace_db.workspace_id,
            parent_file_name=parent_file_name,
            created_datetime_utc=zip_created_datetime_utc,
            tasks=tasks,
            overall_status=DocStatusEnum.not_started,
            docs_total=len(pdf_files),
        ),
        jobs,
    )


async def _get_workspace_jobs(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    redis: aioredis.Redis,
    workspace_name: str,
) -> list[dict]:
    """Return all ingestion jobs in Redis that belong to the workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is checking the status.
    redis
        The Redis client used to track ingestion jobs.
    workspace_name
        The name of the workspace to check the status in.

    Returns
    -------
    list[dict]
        The workspace's jobs, as decoded JSON dictionaries.

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to request ingestion status.
    NotFoundError
        If there are no jobs at all, or none in the workspace.
    """

    workspace_db = await _get_workspace_as_admin(
        asession=asession,
        calling_user_db=calling_user_db,
        forbidden_detail="User does not have the required role to request ingestion "
        "status.",
        workspace_name=workspace_name,
    )

    # Query status response
    job_keys = await redis.keys(f"{JOB_KEY_PREFIX}*")
    if not job_keys:
        raise NotFoundError("No jobs found")

    all_jobs = await redis.mget(job_keys)
    all_jobs_list = [json.loads(job.decode("utf-8")) for job in all_jobs]

    user_workspace_jobs = [
        job for job in all_jobs_list if job["workspace_id"] == workspace_db.workspace_id
    ]

    if len(user_workspace_jobs) == 0:
        raise NotFoundError(f"No jobs found in workspace {workspace_name}")

    return user_workspace_jobs


async def is_job_running(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    redis: aioredis.Redis,
    workspace_name: str,
) -> bool:
    """Check whether any ingestion job in the workspace is in progress.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is checking the status.
    redis
        The Redis client used to track ingestion jobs.
    workspace_name
        The name of the workspace to check the status in.

    Returns
    -------
    bool
        True if any jobs are running, False otherwise.

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to request ingestion status.
    NotFoundError
        If no jobs are found.
    """

    user_workspace_jobs = await _get_workspace_jobs(
        asession=asession,
        calling_user_db=calling_user_db,
        redis=redis,
        workspace_name=workspace_name,
    )

    num_processes_running = sum(
        job["task_status"] == DocStatusEnum.in_progress for job in user_workspace_jobs
    )

    return True if num_processes_running > 0 else False


async def get_all_jobs(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    redis: aioredis.Redis,
    workspace_name: str,
) -> list[DocIngestionStatusZip]:
    """Get the status of all ingestion jobs in the workspace, grouped by upload.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is checking the status.
    redis
        The Redis client used to track ingestion jobs.
    workspace_name
        The name of the workspace to check the status in.

    Returns
    -------
    list[DocIngestionStatusZip]
        One status entry per upload (a single PDF or a .zip of PDFs).

    Raises
    ------
    ForbiddenError
        If the user does not have the required role to request ingestion status.
    NotFoundError
        If no jobs are found.
    """

    user_workspace_jobs = await _get_workspace_jobs(
        asession=asession,
        calling_user_db=calling_user_db,
        redis=redis,
        workspace_name=workspace_name,
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
            task_table.append(
                _single_pdf_upload_status(task=tasks[0], upload_id=upload_id)
            )
        else:
            task_table.append(
                _zip_upload_status(group=group, tasks=tasks, upload_id=upload_id)
            )
    return task_table


def _single_pdf_upload_status(*, task: dict, upload_id: str) -> DocIngestionStatusZip:
    """Build the upload status for an upload that holds a single PDF job.

    Parameters
    ----------
    task
        The single job (decoded JSON from Redis).
    upload_id
        The ID of the upload.

    Returns
    -------
    DocIngestionStatusZip
        The upload status.
    """

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

    return DocIngestionStatusZip.model_validate(zip_task)


def _zip_upload_status(
    *, group: list[dict], tasks: list[dict], upload_id: str
) -> DocIngestionStatusZip:
    """Build the aggregated upload status for an upload with several PDF jobs.

    Parameters
    ----------
    group
        The jobs that belong to the upload.
    tasks
        The same jobs, sorted by creation time.
    upload_id
        The ID of the upload.

    Returns
    -------
    DocIngestionStatusZip
        The aggregated upload status.
    """

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
    num_docs_failed = sum(task["task_status"] == DocStatusEnum.failed for task in tasks)
    num_docs_in_progress = sum(
        task["task_status"] == DocStatusEnum.in_progress for task in tasks
    )
    num_docs_not_started = sum(
        task["task_status"] == DocStatusEnum.not_started for task in tasks
    )

    zip_task["docs_indexed"] = (
        len(tasks) - num_docs_in_progress - num_docs_not_started - num_docs_failed
    )
    zip_task["docs_failed"] = num_docs_failed

    # Overall status precedence: failed > in progress > success > not started.
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

    return DocIngestionStatusZip.model_validate(zip_task)
