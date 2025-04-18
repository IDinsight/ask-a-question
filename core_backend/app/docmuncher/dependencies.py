import json
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Dict

from fastapi import HTTPException, Request, status
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from mistralai import DocumentURLChunk, Mistral
from PyPDF2 import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import (
    LITELLM_MODEL_DOCMUNCHER_PARAPHRASE_TABLE,
    LITELLM_MODEL_DOCMUNCHER_TITLE,
    PAGES_TO_CARDS_CONVERSION,
    REDIS_DOC_INGEST_EXPIRY_TIME,
)
from ..contents.models import save_content_to_db
from ..contents.schemas import ContentCreate
from ..llm_call.llm_prompts import (
    SYSTEM_DOCMUNCHER_TABLE,
    SYSTEM_DOCMUNCHER_TITLE,
    USER_DOCMUNCHER_TABLE,
    USER_DOCMUNCHER_TITLE,
)
from ..llm_call.utils import _ask_llm_async
from ..tags.models import is_tag_name_unique, save_tag_to_db
from ..tags.schemas import TagCreate
from ..utils import setup_logger
from .schemas import DocIngestionStatusPdf, DocStatusEnum
from .utils import is_content_single_line, is_image_only_card, is_table_in_card

logger = setup_logger()
MISTRAL_CLIENT = None
JOB_KEY_PREFIX = "docmuncher_job_"


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    tag = TagCreate(tag_name=filename.upper()[:50])
    if not await is_tag_name_unique(
        asession=asession, tag_name=tag.tag_name, workspace_id=workspace_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag name `{tag.tag_name}` already exists",
        )
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
    HTTPException
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert PDF to markdown: {e}",
        ) from e
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
    HTTPException
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to chunk markdown text: {e}",
        ) from e
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
    HTTPException
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge cards for continuity: {e}",
        ) from e
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
    HTTPException
        If the processing fails.
    """
    final_merged_chunks = []
    for chunk in merged_chunks:
        is_single_line = await is_content_single_line(chunk)
        is_image_card = is_image_only_card(chunk)
        if is_image_card or is_single_line:
            continue

        if is_table_in_card(chunk):
            chunk.page_content = await _ask_llm_async(
                json_=False,
                litellm_model=LITELLM_MODEL_DOCMUNCHER_PARAPHRASE_TABLE,
                metadata=chunk.metadata,
                system_message=SYSTEM_DOCMUNCHER_TABLE,
                user_message=USER_DOCMUNCHER_TABLE.format(
                    meta=json.dumps(chunk.metadata), content=chunk.page_content
                ),
            )
        chunk.metadata["title"] = await _ask_llm_async(
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
    HTTPException
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF file: {e}",
        ) from e
    return {"detail": "Cards saved successfully"}


async def process_pdf_file(
    request: Request,
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
    request
        The request object from FastAPI.
    filename
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
    HTTPException
        If the processing fails.
    """
    # --- Update redis state operations ---
    # Get redis client and the job status
    redis = request.app.state.redis
    job_status = await redis.get(task_id)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

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
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"File `{file_name}` has already been converted.",
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
        logger.error(f"Error processing file {file_name}: {str(e)}")
        await asession.rollback()

        job_status_pydantic.task_status = DocStatusEnum.failed
        job_status_pydantic.error_trace = str(e)
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
