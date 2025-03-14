import json
import os
from typing import List

from fastapi import File, HTTPException, Request, status
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from mistralai import DocumentURLChunk, Mistral
from sqlalchemy.ext.asyncio import AsyncSession

from ..contents.models import save_content_to_db
from ..contents.schemas import ContentCreate
from ..utils import setup_logger
from .schemas import DocStatusEnum, DocUploadResponse

logger = setup_logger()
MISTRAL_CLIENT = None


def get_mistral_client() -> Mistral:
    """
    Get a Mistral client instance.
    """
    global MISTRAL_CLIENT
    if MISTRAL_CLIENT is None:
        MISTRAL_CLIENT = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    return MISTRAL_CLIENT


def convert_pages_to_markdown(file: File) -> dict:
    """
    Convert a PDF file to dictionary of markdown text.

    Parameters
    ----------
    file
        The PDF file to convert.

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
                "file_name": file.filename,
                "content": file.file.read(),
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


def chunk_markdown_text_by_headers(markdown_text: dict) -> list:
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

    md_header_splits: List[Document] = []

    try:
        for page in markdown_text["pages"]:
            markdown = page["markdown"]
            # TODO: test performance with Experimental splitter also
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on, return_each_line=True
            )
            header_splits = markdown_splitter.split_text(markdown)

            for header_split in header_splits:
                metadata = header_split.metadata
                for header in headers_to_split_on:
                    if (
                        (header[1] not in metadata.keys())
                        and (len(md_header_splits) > 0)
                        and (header[1] in md_header_splits[-1].metadata.keys())
                    ):
                        metadata[header[1]] = md_header_splits[-1].metadata[header[1]]
                header_split.metadata = metadata
                md_header_splits.append(header_split)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to chunk markdown text: {e}",
        ) from e
    return md_header_splits


async def convert_markdown_chunks_to_cards(
    md_header_splits: list, tag_id: int, workspace_id: int, asession: AsyncSession
) -> dict:
    """
    Convert markdown chunks to cards.

    Parameters
    ----------
    md_header_splits
        The markdown header splits to convert to cards.
    tag_id:
        The tag ID (associated with the filename) to save the cards with.
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
    for header_split in md_header_splits:
        num_sub_chunks = int(len(header_split.page_content) / 2000 + 1)
        for i in range(num_sub_chunks):
            try:
                title = "--".join(
                    [str(v) for v in header_split.metadata.values()]
                    + [header_split.page_content[:10]]
                )
                metadata = header_split.metadata
                metadata["sub_chunk"] = i

                card = ContentCreate(
                    content_text=header_split.page_content[i * 2000 : (i + 1) * 2000],
                    content_title=title,
                    content_metadata=metadata,
                    context_tags=[tag_id],
                )
                await save_content_to_db(
                    asession=asession,
                    content=card,
                    exclude_archived=True,
                    workspace_id=workspace_id,
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
    task_id: int,
    file: File,
    tag_id: int,
    workspace_id: int,
    asession: AsyncSession,
) -> DocUploadResponse:
    """
    Process a PDF file.

    Parameters
    ----------
    request
        The request object from FastAPI.
    file
        The PDF file to process.
    tag_id
        The tag ID (associated with the filename) to save the cards with.
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
    # Update redis state operations
    redis = request.app.state.redis
    job_status = await redis.get(task_id)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    job_status_pydantic = DocUploadResponse.model_validate(
        json.loads(job_status.decode("utf-8"))
    )
    job_status_pydantic.status = DocStatusEnum.in_progress
    await redis.set(task_id, job_status_pydantic.model_dump_json())

    # Process PDF
    try:
        markdown_text = convert_pages_to_markdown(file)
        md_header_splits = chunk_markdown_text_by_headers(markdown_text)
        await convert_markdown_chunks_to_cards(
            md_header_splits=md_header_splits,
            tag_id=tag_id,
            workspace_id=workspace_id,
            asession=asession,
        )

    except Exception as e:
        job_status_pydantic.status = DocStatusEnum.failed
        await redis.set(task_id, job_status_pydantic.model_dump_json())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF file: {e}",
        ) from e

    job_status_pydantic.status = DocStatusEnum.success
    await redis.set(task_id, job_status_pydantic.model_dump_json())

    return job_status
