"""Unit tests for `app.docmuncher.service`.

No database, network, Mistral or LLM calls: repositories, the Mistral client and
`ask_llm_async` are replaced with mocks, and Redis with the in-memory `FakeRedis`
from the local conftest.
"""

import json
from datetime import datetime, timezone
from http import HTTPStatus
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Callable, Mapping
from unittest.mock import AsyncMock, MagicMock
from zipfile import ZipFile

import pytest
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.service import ExceedsContentQuotaError
from app.core.config import PAGES_TO_CARDS_CONVERSION, REDIS_DOC_INGEST_EXPIRY_TIME
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.docmuncher import service
from app.docmuncher.schemas import (
    DocIngestionStatusPdf,
    DocStatusEnum,
    DocUploadResponsePdf,
    DocUploadResponseZip,
)
from tests.docmuncher.conftest import FakeRedis

WORKSPACE_ID = 7
WORKSPACE_NAME = "docmuncher_workspace"


def _await_kwargs(mock: AsyncMock) -> Mapping[str, Any]:
    """Return the keyword arguments of the mock's last await.

    Parameters
    ----------
    mock
        The awaited mock.

    Returns
    -------
    Mapping[str, Any]
        The keyword arguments.
    """

    assert mock.await_args is not None, "mock was never awaited"
    return mock.await_args.kwargs


# Helpers.
def _doc(content: str, **metadata: Any) -> Document:
    """Build a langchain document.

    Parameters
    ----------
    content
        The page content.
    metadata
        The document metadata.

    Returns
    -------
    Document
        The document.
    """

    return Document(page_content=content, metadata=metadata)


def _workspace(content_quota: int | None = 50) -> Any:
    """Build a stand-in for `WorkspaceDB` with the attributes the service reads.

    Parameters
    ----------
    content_quota
        The workspace content quota.

    Returns
    -------
    Any
        The fake workspace.
    """

    return SimpleNamespace(workspace_id=WORKSPACE_ID, content_quota=content_quota)


def _job(**overrides: Any) -> dict[str, Any]:
    """Build a job record as stored in Redis once processing has started.

    Parameters
    ----------
    overrides
        Fields to override.

    Returns
    -------
    dict[str, Any]
        The job record.
    """

    job: dict[str, Any] = {
        "upload_id": "upload-1",
        "user_id": 1,
        "workspace_id": WORKSPACE_ID,
        "parent_file_name": None,
        "created_datetime_utc": "2025-01-01T00:00:00+00:00",
        "task_id": "docmuncher_job_1",
        "doc_name": "doc.pdf",
        "task_status": DocStatusEnum.success.value,
        "error_trace": "",
        "finished_datetime_utc": "2025-01-01T00:05:00+00:00",
    }
    job.update(overrides)
    return job


async def _store_jobs(redis: FakeRedis, jobs: list[dict[str, Any]]) -> None:
    """Write job records to the fake Redis under the docmuncher key prefix.

    Parameters
    ----------
    redis
        The fake Redis.
    jobs
        The job records to store.
    """

    for i, job in enumerate(jobs):
        await redis.set(f"{service.JOB_KEY_PREFIX}{i}", json.dumps(job))


def _fake_mistral(ocr_json: str) -> MagicMock:
    """Build a fake Mistral client whose OCR call returns `ocr_json`.

    Parameters
    ----------
    ocr_json
        The JSON string returned by the OCR response's `model_dump_json`.

    Returns
    -------
    MagicMock
        The fake client.
    """

    client = MagicMock()
    client.files.upload.return_value = SimpleNamespace(id="file-1")
    client.files.get_signed_url.return_value = SimpleNamespace(
        url="https://example.com/signed.pdf"
    )
    client.ocr.process.return_value.model_dump_json.return_value = ocr_json
    return client


async def _fake_llm(**kwargs: Any) -> str:
    """Stand in for `ask_llm_async`, answering according to the prompt used.

    Single-line checks answer "True" only for content containing "Caption"; table
    paraphrasing and title generation return fixed strings.

    Parameters
    ----------
    kwargs
        The keyword arguments `ask_llm_async` is called with.

    Returns
    -------
    str
        The fake LLM output.
    """

    if kwargs["system_message"] == service.SYSTEM_SINGLE_LINE_CARD:
        return "True" if "Caption" in kwargs["user_message"] else "False"
    if kwargs["system_message"] == service.SYSTEM_DOCMUNCHER_TABLE:
        return "Paraphrased table"
    return '"A title"'


# Fixtures.
@pytest.fixture
def admin_in_workspace(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Make the calling user an admin of a fake workspace.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    Any
        The fake workspace returned by the workspace lookup.
    """

    workspace = _workspace()
    monkeypatch.setattr(
        service,
        "get_workspace_by_workspace_name",
        AsyncMock(return_value=workspace),
    )
    monkeypatch.setattr(
        service, "user_has_required_role_in_workspace", AsyncMock(return_value=True)
    )
    return workspace


@pytest.fixture
def quota_check(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace the content quota check and the background session factory.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    AsyncMock
        The mocked `_check_content_quota_availability`.
    """

    check = AsyncMock()
    monkeypatch.setattr(service, "_check_content_quota_availability", check)
    # Each job opens its own `AsyncSession`; a mock avoids needing a real engine.
    monkeypatch.setattr(service, "AsyncSession", MagicMock(name="AsyncSession"))
    monkeypatch.setattr(service, "CHECK_CONTENT_LIMIT", True)
    return check


@pytest.fixture
def asession() -> MagicMock:
    """Return a mock async session (async methods become `AsyncMock`).

    Returns
    -------
    MagicMock
        The mock session.
    """

    session = MagicMock(spec=AsyncSession)
    # `bind` is an instance attribute, so the class spec does not provide it.
    session.bind = MagicMock(name="bind")
    return session


@pytest.fixture
async def job_in_redis(fake_redis: FakeRedis) -> str:
    """Store a freshly created (not started) job and a pending-contents counter.

    Parameters
    ----------
    fake_redis
        The fake Redis.

    Returns
    -------
    str
        The job's task ID.
    """

    task_id = f"{service.JOB_KEY_PREFIX}abc"
    job = DocUploadResponsePdf(
        upload_id="upload-1",
        user_id=1,
        workspace_id=WORKSPACE_ID,
        created_datetime_utc=datetime.now(timezone.utc),
        task_id=task_id,
        doc_name="guide.pdf",
    )
    await fake_redis.set(task_id, job.model_dump_json())
    await fake_redis.set(f"{WORKSPACE_ID}_docmuncher_contents", 10)
    return task_id


# Small pure helpers.
@pytest.mark.parametrize(
    "error, expected",
    [
        (BadRequestError("bad input"), "400: bad input"),
        (AppError("busy", status_code=HTTPStatus.LOCKED), "423: busy"),
        (ValueError("boom"), "boom"),
    ],
)
def test_format_error(error: Exception, expected: str) -> None:
    """Domain errors are prefixed with their status code; others are stringified.

    Parameters
    ----------
    error
        The exception to format.
    expected
        The expected message.
    """

    assert service._format_error(error) == expected


def test_get_mistral_client_is_created_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Mistral client is built lazily with the API key and then cached.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    mistral_cls = MagicMock()
    monkeypatch.setattr(service, "MISTRAL_CLIENT", None)
    monkeypatch.setattr(service, "Mistral", mistral_cls)
    monkeypatch.setenv("MISTRAL_API_KEY", "[API_KEY]")

    first = service.get_mistral_client()
    second = service.get_mistral_client()

    assert first is second is mistral_cls.return_value
    mistral_cls.assert_called_once_with(api_key="[API_KEY]")


@pytest.mark.parametrize(
    "content, expected",
    [
        ("![figure](image.png)", True),
        ("<img src='image.png'>", True),
        ("   ", True),
        ("![figure](image.png) with a caption", False),
        ("Plain text", False),
    ],
)
def test_is_image_only_card(content: str, expected: bool) -> None:
    """Cards with nothing but image markup are detected.

    Parameters
    ----------
    content
        The card content.
    expected
        Whether the card is image-only.
    """

    assert service.is_image_only_card(_doc(content)) is expected


@pytest.mark.parametrize(
    "content, expected",
    [
        ("| a | b |", True),
        ("+---+---+", True),
        ("Intro\n--- | ---", True),
        ("a | b", False),
        ("No table here", False),
    ],
)
def test_is_table_in_card(content: str, expected: bool) -> None:
    """Markdown and ASCII tables are detected on any line.

    Parameters
    ----------
    content
        The card content.
    expected
        Whether the card contains a table.
    """

    assert service.is_table_in_card(_doc(content)) is expected


async def test_is_content_single_line_skips_llm_for_multiline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multi-line content is never a caption, so the LLM is not asked.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    llm = AsyncMock()
    monkeypatch.setattr(service, "ask_llm_async", llm)

    assert await service.is_content_single_line(_doc("line one\nline two")) is False
    llm.assert_not_awaited()


@pytest.mark.parametrize("llm_answer, expected", [("True", True), ("False", False)])
async def test_is_content_single_line_uses_llm_verdict(
    monkeypatch: pytest.MonkeyPatch, llm_answer: str, expected: bool
) -> None:
    """For a single line, the LLM decides whether it is a caption.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    llm_answer
        The LLM's raw answer.
    expected
        The expected verdict.
    """

    llm = AsyncMock(return_value=llm_answer)
    monkeypatch.setattr(service, "ask_llm_async", llm)

    assert await service.is_content_single_line(_doc("  Figure 1  ")) is expected
    assert "Figure 1" in _await_kwargs(llm)["user_message"]


# Tags.
async def test_create_tag_per_file_requires_filename(asession: MagicMock) -> None:
    """An empty filename is rejected.

    Parameters
    ----------
    asession
        Mock async session.
    """

    with pytest.raises(BadRequestError, match="Filename is required"):
        await service.create_tag_per_file(
            filename="", workspace_id=WORKSPACE_ID, asession=asession
        )


async def test_create_tag_per_file_rejects_duplicate_tag(
    asession: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file whose tag already exists in the workspace is rejected.

    Parameters
    ----------
    asession
        Mock async session.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr(service, "is_tag_name_unique", AsyncMock(return_value=False))

    with pytest.raises(BadRequestError) as exc_info:
        await service.create_tag_per_file(
            filename="guide.pdf", workspace_id=WORKSPACE_ID, asession=asession
        )
    assert exc_info.value.detail == "Tag name `GUIDE.PDF` already exists"


async def test_create_tag_per_file_saves_truncated_uppercase_tag(
    asession: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tag is the upper-cased filename cut to 50 characters, saved uncommitted.

    Parameters
    ----------
    asession
        Mock async session.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    tag_db = object()
    save_tag = AsyncMock(return_value=tag_db)
    monkeypatch.setattr(service, "is_tag_name_unique", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "save_tag_to_db", save_tag)

    result = await service.create_tag_per_file(
        filename="a" * 60 + ".pdf", workspace_id=WORKSPACE_ID, asession=asession
    )

    assert result == [tag_db]
    kwargs = _await_kwargs(save_tag)
    assert kwargs["tag"].tag_name == "A" * 50
    assert kwargs["commmit"] is False
    assert kwargs["workspace_id"] == WORKSPACE_ID


# PDF -> markdown -> chunks.
def test_convert_pages_to_markdown_runs_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    """The PDF is uploaded, signed and OCR'd; the OCR JSON is returned as a dict.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    client = _fake_mistral('{"pages": [{"markdown": "# Hi"}]}')
    monkeypatch.setattr(service, "get_mistral_client", lambda: client)

    result = service.convert_pages_to_markdown(file_name="a.pdf", content=b"%PDF")

    assert result == {"pages": [{"markdown": "# Hi"}]}
    client.files.upload.assert_called_once_with(
        file={"file_name": "a.pdf", "content": b"%PDF"}, purpose="ocr"
    )
    client.files.get_signed_url.assert_called_once_with(file_id="file-1")
    ocr_kwargs = client.ocr.process.call_args.kwargs
    assert ocr_kwargs["model"] == "mistral-ocr-latest"
    assert ocr_kwargs["document"].document_url == "https://example.com/signed.pdf"


def test_convert_pages_to_markdown_wraps_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any Mistral failure becomes an `InternalServerError`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    client = _fake_mistral("{}")
    client.files.upload.side_effect = RuntimeError("quota exhausted")
    monkeypatch.setattr(service, "get_mistral_client", lambda: client)

    with pytest.raises(InternalServerError, match="quota exhausted"):
        service.convert_pages_to_markdown(file_name="a.pdf", content=b"%PDF")


def test_chunk_markdown_text_by_headers() -> None:
    """Each line becomes a chunk tagged with its page, index and headers."""

    markdown = {
        "pages": [
            {"markdown": "# Intro\nFirst line\n## Sub\nSecond line\n# Next\nThird"},
            {"markdown": "Carry on\n# P2\nMore"},
        ]
    }

    splits = service.chunk_markdown_text_by_headers(markdown)

    assert [len(page) for page in splits.values()] == [3, 2]
    assert splits[0][0].page_content == "First line"
    assert splits[0][0].metadata == {"Header 1": "Intro", "page": 0, "chunk": 0}
    assert splits[0][1].metadata["Header 2"] == "Sub"
    # A header missing from a chunk is copied from the previous chunk on the page.
    assert splits[0][2].metadata["Header 1"] == "Next"
    assert splits[0][2].metadata["Header 2"] == "Sub"
    assert splits[1][0].metadata == {"page": 1, "chunk": 0}


def test_chunk_markdown_text_by_headers_wraps_errors() -> None:
    """Malformed OCR output becomes an `InternalServerError`."""

    with pytest.raises(InternalServerError, match="Failed to chunk markdown text"):
        service.chunk_markdown_text_by_headers({"no_pages": []})


async def test_merge_chunks_for_continuity_joins_across_pages() -> None:
    """The last chunk of a page is merged with the first chunk of the next page."""

    splits = {
        0: {
            0: _doc("Alpha", page=0, chunk=0),
            1: _doc("Bravo", page=0, chunk=1, **{"Header 1": "H"}),
        },
        1: {0: _doc(" Charlie", page=1, chunk=0, **{"Header 2": "S"})},
    }

    merged = await service.merge_chunks_for_continuity(splits)

    assert merged[0].page_content == "Alpha"
    assert merged[1].page_content == "Bravo Charlie"
    # Headers from both chunks are kept, but page/chunk stay those of the first.
    assert merged[1].metadata == {
        "page": 0,
        "chunk": 1,
        "Header 1": "H",
        "Header 2": "S",
        "title": "Placeholder title",
    }
    assert merged[-1].page_content == " Charlie"


async def test_merge_chunks_for_continuity_wraps_errors() -> None:
    """An empty following page cannot be merged and raises `InternalServerError`."""

    splits = {0: {0: _doc("Alpha", page=0, chunk=0)}, 1: {}}

    with pytest.raises(InternalServerError, match="Failed to merge cards"):
        await service.merge_chunks_for_continuity(splits)


async def test_deal_with_incorrectly_formatted_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Image-only and caption cards are dropped; tables are paraphrased; all
    remaining cards get an LLM title with surrounding quotes stripped.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr(service, "ask_llm_async", AsyncMock(side_effect=_fake_llm))
    chunks = [
        _doc("![figure](image.png)", page=0),
        _doc("Figure Caption", page=0),
        _doc("| a | b |\n|---|---|\n| 1 | 2 |", page=1),
        _doc("Line one\nLine two", page=1),
    ]

    result = await service.deal_with_incorrectly_formatted_cards(chunks)

    assert [c.page_content for c in result] == [
        "Paraphrased table",
        "Line one\nLine two",
    ]
    assert all(c.metadata["title"] == "A title" for c in result)


async def test_convert_markdown_chunks_to_cards_saves_each_card(
    asession: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each chunk is saved as an unvalidated content card with the file's tags.

    Parameters
    ----------
    asession
        Mock async session.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    save_content = AsyncMock()
    monkeypatch.setattr(service, "save_content_to_db", save_content)
    tags = [object()]

    result = await service.convert_markdown_chunks_to_cards(
        merged_chunks=[_doc("Body", title="Title", page=0)],
        content_tags=tags,
        workspace_id=WORKSPACE_ID,
        asession=asession,
    )

    assert result == {"detail": "Cards saved successfully"}
    kwargs = _await_kwargs(save_content)
    card = kwargs["content"]
    assert (card.content_title, card.content_text) == ("Title", "Body")
    assert card.content_metadata == {"page": 0}
    assert card.content_tags == tags
    assert card.is_validated is False
    assert kwargs["commit"] is False and kwargs["exclude_archived"] is True


async def test_convert_markdown_chunks_to_cards_wraps_errors(
    asession: MagicMock,
) -> None:
    """A chunk without a title cannot become a card.

    Parameters
    ----------
    asession
        Mock async session.
    """

    with pytest.raises(InternalServerError, match="Failed to process PDF file"):
        await service.convert_markdown_chunks_to_cards(
            merged_chunks=[_doc("Body")],
            content_tags=[],
            workspace_id=WORKSPACE_ID,
            asession=asession,
        )


# Background job.
async def test_process_pdf_file_requires_job(
    asession: MagicMock, fake_redis: FakeRedis
) -> None:
    """A task ID unknown to Redis raises `NotFoundError`.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    """

    with pytest.raises(NotFoundError, match="Job not found"):
        await service.process_pdf_file(
            redis=fake_redis,  # type: ignore[arg-type]
            task_id="missing",
            file_name="a.pdf",
            content=b"",
            workspace_id=WORKSPACE_ID,
            asession=asession,
        )


async def test_process_pdf_file_success(
    asession: MagicMock,
    fake_redis: FakeRedis,
    job_in_redis: str,
    make_pdf: Callable[[int], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The full pipeline turns OCR'd pages into saved cards and marks success.

    Only the edges are mocked (Mistral, LLM, tag and content repositories); the
    chunking, merging and filtering steps run for real.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    job_in_redis
        Task ID of the stored job.
    make_pdf
        PDF factory.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    ocr = {"pages": [{"markdown": "# Intro\nLine one\nLine two"}, {"markdown": "End"}]}
    monkeypatch.setattr(
        service, "get_mistral_client", lambda: _fake_mistral(json.dumps(ocr))
    )
    monkeypatch.setattr(service, "ask_llm_async", AsyncMock(side_effect=_fake_llm))
    monkeypatch.setattr(service, "is_tag_name_unique", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "save_tag_to_db", AsyncMock(return_value=object()))
    save_content = AsyncMock()
    monkeypatch.setattr(service, "save_content_to_db", save_content)

    status = await service.process_pdf_file(
        redis=fake_redis,  # type: ignore[arg-type]
        task_id=job_in_redis,
        file_name="guide.pdf",
        content=make_pdf(2),
        workspace_id=WORKSPACE_ID,
        asession=asession,
    )

    assert status.task_status == DocStatusEnum.success
    assert status.error_trace == ""
    assert status.finished_datetime_utc is not None
    stored = DocIngestionStatusPdf.model_validate_json(fake_redis.store[job_in_redis])
    assert stored.task_status == DocStatusEnum.success
    # Every surviving multi-line chunk was saved; nothing was committed per card.
    assert save_content.await_count > 0
    asession.commit.assert_awaited_once()
    asession.rollback.assert_not_awaited()
    asession.close.assert_awaited_once()
    # The lock stays so the same file is not converted twice.
    assert "lock:guide.pdf" in fake_redis.store
    # 2 pages finished, so the pending-contents counter drops by 2 pages' worth.
    expected = 10 - 2 * PAGES_TO_CARDS_CONVERSION
    assert fake_redis.store[f"{WORKSPACE_ID}_docmuncher_contents"] == (
        str(expected).encode()
    )


async def test_process_pdf_file_rejects_locked_file(
    asession: MagicMock,
    fake_redis: FakeRedis,
    job_in_redis: str,
    make_pdf: Callable[[int], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file that is already locked fails the job without running OCR.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    job_in_redis
        Task ID of the stored job.
    make_pdf
        PDF factory.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    convert = MagicMock()
    monkeypatch.setattr(service, "convert_pages_to_markdown", convert)
    await fake_redis.set("lock:guide.pdf", "1")

    status = await service.process_pdf_file(
        redis=fake_redis,  # type: ignore[arg-type]
        task_id=job_in_redis,
        file_name="guide.pdf",
        content=make_pdf(1),
        workspace_id=WORKSPACE_ID,
        asession=asession,
    )

    assert status.task_status == DocStatusEnum.failed
    assert status.error_trace == "423: File `guide.pdf` has already been converted."
    convert.assert_not_called()


async def test_process_pdf_file_failure_rolls_back_and_releases_lock(
    asession: MagicMock,
    fake_redis: FakeRedis,
    job_in_redis: str,
    make_pdf: Callable[[int], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pipeline error marks the job failed, rolls back, releases the lock and
    never lets the pending-contents counter go negative.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    job_in_redis
        Task ID of the stored job.
    make_pdf
        PDF factory.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr(
        service,
        "convert_pages_to_markdown",
        MagicMock(side_effect=InternalServerError("OCR down")),
    )
    await fake_redis.set(f"{WORKSPACE_ID}_docmuncher_contents", 1)

    status = await service.process_pdf_file(
        redis=fake_redis,  # type: ignore[arg-type]
        task_id=job_in_redis,
        file_name="guide.pdf",
        content=make_pdf(3),
        workspace_id=WORKSPACE_ID,
        asession=asession,
    )

    assert status.task_status == DocStatusEnum.failed
    assert status.error_trace == "500: OCR down"
    assert status.finished_datetime_utc is not None
    asession.rollback.assert_awaited_once()
    asession.commit.assert_not_awaited()
    asession.close.assert_awaited_once()
    assert "lock:guide.pdf" not in fake_redis.store
    assert fake_redis.store[f"{WORKSPACE_ID}_docmuncher_contents"] == b"0"


# Upload authorisation.
async def test_get_workspace_as_admin_forbids_non_admin(
    asession: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user without the admin role gets the caller-supplied 403 detail.

    Parameters
    ----------
    asession
        Mock async session.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr(
        service, "get_workspace_by_workspace_name", AsyncMock(return_value=object())
    )
    monkeypatch.setattr(
        service, "user_has_required_role_in_workspace", AsyncMock(return_value=False)
    )

    with pytest.raises(ForbiddenError) as exc_info:
        await service._get_workspace_as_admin(
            asession=asession,
            calling_user_db=MagicMock(),
            forbidden_detail="Nope.",
            workspace_name=WORKSPACE_NAME,
        )
    assert exc_info.value.detail == "Nope."


@pytest.mark.parametrize("filename", ["guide.pdf", "bundle.zip"])
async def test_authorize_document_upload_accepts_pdf_and_zip(
    admin_in_workspace: Any, asession: MagicMock, filename: str
) -> None:
    """PDF and zip uploads by an admin return the workspace.

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    filename
        The uploaded filename.
    """

    workspace = await service.authorize_document_upload(
        asession=asession,
        calling_user_db=MagicMock(),
        filename=filename,
        workspace_name=WORKSPACE_NAME,
    )

    assert workspace is admin_in_workspace


@pytest.mark.parametrize(
    "filename, detail",
    [
        (None, "Filename is required"),
        ("", "Filename is required"),
        ("notes.txt", "Only PDF files are supported for document ingestion."),
    ],
)
async def test_authorize_document_upload_rejects_bad_filenames(
    admin_in_workspace: Any, asession: MagicMock, filename: str | None, detail: str
) -> None:
    """Missing names and non-PDF/zip files are rejected with 400.

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    filename
        The uploaded filename.
    detail
        The expected error detail.
    """

    with pytest.raises(BadRequestError) as exc_info:
        await service.authorize_document_upload(
            asession=asession,
            calling_user_db=MagicMock(),
            filename=filename,
            workspace_name=WORKSPACE_NAME,
        )
    assert exc_info.value.detail == detail


# Job creation.
async def test_create_ingestion_jobs_single_pdf(
    asession: MagicMock,
    fake_redis: FakeRedis,
    make_pdf: Callable[[int], bytes],
    quota_check: AsyncMock,
) -> None:
    """A single PDF yields one job, logged in Redis, counted against the quota.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    make_pdf
        PDF factory.
    quota_check
        The mocked content quota check.
    """

    content = make_pdf(3)
    # Contents already expected from jobs still running are added on top.
    await fake_redis.set(f"{WORKSPACE_ID}_docmuncher_contents", 4)

    response, jobs = await service.create_ingestion_jobs(
        asession=asession,
        calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
        file_content=content,
        filename="guide.pdf",
        redis=fake_redis,  # type: ignore[arg-type]
        workspace_db=_workspace(),
    )

    expected_contents = 3 * PAGES_TO_CARDS_CONVERSION + 4
    assert isinstance(response, DocUploadResponsePdf)
    assert (response.doc_name, response.parent_file_name) == ("guide.pdf", None)
    assert response.task_status == DocStatusEnum.not_started
    assert len(jobs) == 1
    assert jobs[0].task_id == response.task_id
    assert jobs[0].task_id.startswith(service.JOB_KEY_PREFIX)
    assert (jobs[0].file_name, jobs[0].content) == ("guide.pdf", content)
    session_factory: Any = service.AsyncSession  # The mock set by `quota_check`.
    assert jobs[0].asession is session_factory.return_value
    session_factory.assert_called_once_with(asession.bind)
    assert fake_redis.expiry[response.task_id] == REDIS_DOC_INGEST_EXPIRY_TIME
    assert fake_redis.store[f"{WORKSPACE_ID}_docmuncher_contents"] == (
        str(expected_contents).encode()
    )
    assert _await_kwargs(quota_check)["n_contents_to_add"] == expected_contents


async def test_create_ingestion_jobs_zip(
    asession: MagicMock,
    fake_redis: FakeRedis,
    make_pdf: Callable[[int], bytes],
    quota_check: AsyncMock,
) -> None:
    """A zip yields one job per PDF inside it; other files are ignored.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    make_pdf
        PDF factory.
    quota_check
        The mocked content quota check.
    """

    buffer = BytesIO()
    with ZipFile(buffer, "w") as zip_file:
        zip_file.writestr("a.pdf", make_pdf(1))
        zip_file.writestr("b.pdf", make_pdf(2))
        zip_file.writestr("readme.txt", "ignored")

    response, jobs = await service.create_ingestion_jobs(
        asession=asession,
        calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
        file_content=buffer.getvalue(),
        filename="bundle.zip",
        redis=fake_redis,  # type: ignore[arg-type]
        workspace_db=_workspace(),
    )

    assert isinstance(response, DocUploadResponseZip)
    assert response.docs_total == 2
    assert response.parent_file_name == "bundle.zip"
    assert [t.doc_name for t in response.tasks] == ["a.pdf", "b.pdf"]
    assert {t.upload_id for t in response.tasks} == {response.upload_id}
    assert [j.file_name for j in jobs] == ["a.pdf", "b.pdf"]
    assert _await_kwargs(quota_check)["n_contents_to_add"] == (
        3 * PAGES_TO_CARDS_CONVERSION
    )


async def test_create_ingestion_jobs_zip_without_pdfs(
    asession: MagicMock, fake_redis: FakeRedis, quota_check: AsyncMock
) -> None:
    """A zip with no PDFs in it is rejected.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    quota_check
        The mocked content quota check.
    """

    buffer = BytesIO()
    with ZipFile(buffer, "w") as zip_file:
        zip_file.writestr("readme.txt", "no pdfs")

    with pytest.raises(BadRequestError, match="does not contain any PDF files"):
        await service.create_ingestion_jobs(
            asession=asession,
            calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
            file_content=buffer.getvalue(),
            filename="bundle.zip",
            redis=fake_redis,  # type: ignore[arg-type]
            workspace_db=_workspace(),
        )


async def test_create_ingestion_jobs_page_quota_exceeded(
    asession: MagicMock,
    fake_redis: FakeRedis,
    make_pdf: Callable[[int], bytes],
    quota_check: AsyncMock,
) -> None:
    """More pages than the quota allows is rejected before any job is logged.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    make_pdf
        PDF factory.
    quota_check
        The mocked content quota check.
    """

    with pytest.raises(ForbiddenError, match="exceeds page quota"):
        await service.create_ingestion_jobs(
            asession=asession,
            calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
            file_content=make_pdf(3),
            filename="guide.pdf",
            redis=fake_redis,  # type: ignore[arg-type]
            workspace_db=_workspace(content_quota=PAGES_TO_CARDS_CONVERSION * 2),
        )
    quota_check.assert_not_awaited()
    assert fake_redis.store == {}


@pytest.mark.parametrize(
    "quota_message, existing",
    [
        ("Adding 6 new contents to the already existing 7 in the database ...", 7),
        ("Adding 6 new contents to the database would exceed the limit.", 0),
    ],
)
async def test_create_ingestion_jobs_content_quota_exceeded(
    asession: MagicMock,
    fake_redis: FakeRedis,
    make_pdf: Callable[[int], bytes],
    quota_check: AsyncMock,
    quota_message: str,
    existing: int,
) -> None:
    """A content quota error is turned into a 403 that says how many pages fit.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    make_pdf
        PDF factory.
    quota_check
        The mocked content quota check.
    quota_message
        The message of the `ExceedsContentQuotaError`.
    existing
        Number of existing contents the message reports.
    """

    quota_check.side_effect = ExceedsContentQuotaError(quota_message)
    await fake_redis.set(f"{WORKSPACE_ID}_docmuncher_contents", 4)

    with pytest.raises(ForbiddenError) as exc_info:
        await service.create_ingestion_jobs(
            asession=asession,
            calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
            file_content=make_pdf(3),
            filename="guide.pdf",
            redis=fake_redis,  # type: ignore[arg-type]
            workspace_db=_workspace(content_quota=20),
        )

    # quota - contents pending from running jobs - existing contents, in pages.
    pages_left = (20 - 4 - existing) // PAGES_TO_CARDS_CONVERSION
    assert exc_info.value.detail.endswith(f"{pages_left} more pages are allowed.")


@pytest.mark.parametrize(
    "check_limit, content_quota, expect_check",
    [(False, 1, False), (True, None, True)],
)
async def test_create_ingestion_jobs_skips_quota_checks(
    asession: MagicMock,
    fake_redis: FakeRedis,
    make_pdf: Callable[[int], bytes],
    quota_check: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    check_limit: bool,
    content_quota: int | None,
    expect_check: bool,
) -> None:
    """Checks are skipped when disabled; the page check needs a quota to apply.

    Parameters
    ----------
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    make_pdf
        PDF factory.
    quota_check
        The mocked content quota check.
    monkeypatch
        Pytest monkeypatch fixture.
    check_limit
        Value of `CHECK_CONTENT_LIMIT`.
    content_quota
        The workspace content quota.
    expect_check
        Whether the content quota check should run.
    """

    monkeypatch.setattr(service, "CHECK_CONTENT_LIMIT", check_limit)

    _, jobs = await service.create_ingestion_jobs(
        asession=asession,
        calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
        file_content=make_pdf(3),
        filename="guide.pdf",
        redis=fake_redis,  # type: ignore[arg-type]
        workspace_db=_workspace(content_quota=content_quota),
    )

    assert len(jobs) == 1
    assert quota_check.await_count == int(expect_check)


# Job status.
async def test_job_status_without_any_jobs(
    admin_in_workspace: Any, asession: MagicMock, fake_redis: FakeRedis
) -> None:
    """With no jobs in Redis at all, a 404 is raised.

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    """

    with pytest.raises(NotFoundError, match="No jobs found"):
        await service.is_job_running(
            asession=asession,
            calling_user_db=MagicMock(),
            redis=fake_redis,  # type: ignore[arg-type]
            workspace_name=WORKSPACE_NAME,
        )


async def test_job_status_ignores_other_workspaces(
    admin_in_workspace: Any, asession: MagicMock, fake_redis: FakeRedis
) -> None:
    """Jobs from other workspaces are invisible, so a 404 is raised.

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    """

    await _store_jobs(fake_redis, [_job(workspace_id=WORKSPACE_ID + 1)])

    with pytest.raises(NotFoundError) as exc_info:
        await service.get_all_jobs(
            asession=asession,
            calling_user_db=MagicMock(),
            redis=fake_redis,  # type: ignore[arg-type]
            workspace_name=WORKSPACE_NAME,
        )
    assert exc_info.value.detail == f"No jobs found in workspace {WORKSPACE_NAME}"


@pytest.mark.parametrize(
    "statuses, expected",
    [
        ([DocStatusEnum.success, DocStatusEnum.in_progress], True),
        ([DocStatusEnum.success, DocStatusEnum.failed], False),
    ],
)
async def test_is_job_running(
    admin_in_workspace: Any,
    asession: MagicMock,
    fake_redis: FakeRedis,
    statuses: list[DocStatusEnum],
    expected: bool,
) -> None:
    """A workspace has a running job when any of its jobs is in progress.

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    statuses
        Status of each stored job.
    expected
        Whether a job is reported as running.
    """

    await _store_jobs(fake_redis, [_job(task_status=s.value) for s in statuses])

    assert (
        await service.is_job_running(
            asession=asession,
            calling_user_db=MagicMock(),
            redis=fake_redis,  # type: ignore[arg-type]
            workspace_name=WORKSPACE_NAME,
        )
        is expected
    )


async def test_get_all_jobs_groups_by_upload(
    admin_in_workspace: Any, asession: MagicMock, fake_redis: FakeRedis
) -> None:
    """Jobs are grouped into one status entry per upload (single PDF or zip).

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    """

    await _store_jobs(
        fake_redis,
        [
            _job(upload_id="u1", doc_name="single.pdf"),
            _job(upload_id="u2", doc_name="b.pdf", parent_file_name="bundle.zip"),
            _job(upload_id="u2", doc_name="a.pdf", parent_file_name="bundle.zip"),
        ],
    )

    statuses = await service.get_all_jobs(
        asession=asession,
        calling_user_db=MagicMock(),
        redis=fake_redis,  # type: ignore[arg-type]
        workspace_name=WORKSPACE_NAME,
    )

    by_upload = {s.upload_id: s for s in statuses}
    assert by_upload["u1"].parent_file_name == "single.pdf"
    assert by_upload["u1"].docs_total == 1
    assert by_upload["u2"].parent_file_name == "bundle.zip"
    assert by_upload["u2"].docs_total == 2
    assert by_upload["u2"].overall_status == DocStatusEnum.success


@pytest.mark.xfail(
    raises=KeyError,
    strict=True,
    reason="App bug: a job that has not started yet has no `error_trace` / "
    "`finished_datetime_utc` in Redis, and `_single_pdf_upload_status` indexes "
    "them directly.",
)
async def test_get_all_jobs_right_after_upload(
    admin_in_workspace: Any,
    asession: MagicMock,
    fake_redis: FakeRedis,
    make_pdf: Callable[[int], bytes],
    quota_check: AsyncMock,
) -> None:
    """Status can be read for a single-PDF upload before its job has started.

    Parameters
    ----------
    admin_in_workspace
        The fake workspace the user is an admin of.
    asession
        Mock async session.
    fake_redis
        The fake Redis.
    make_pdf
        PDF factory.
    quota_check
        The mocked content quota check.
    """

    await service.create_ingestion_jobs(
        asession=asession,
        calling_user_db=SimpleNamespace(user_id=1),  # type: ignore[arg-type]
        file_content=make_pdf(1),
        filename="guide.pdf",
        redis=fake_redis,  # type: ignore[arg-type]
        workspace_db=admin_in_workspace,
    )

    statuses = await service.get_all_jobs(
        asession=asession,
        calling_user_db=MagicMock(),
        redis=fake_redis,  # type: ignore[arg-type]
        workspace_name=WORKSPACE_NAME,
    )
    assert statuses[0].overall_status == DocStatusEnum.not_started


@pytest.mark.parametrize(
    "status, docs_indexed",
    [
        (DocStatusEnum.success, 1),
        (DocStatusEnum.in_progress, 0),
        (DocStatusEnum.not_started, 0),
    ],
)
def test_single_pdf_upload_status(status: DocStatusEnum, docs_indexed: int) -> None:
    """A single-PDF upload reports its job's status and indexing count.

    Parameters
    ----------
    status
        The job status.
    docs_indexed
        Expected number of indexed documents.
    """

    result = service._single_pdf_upload_status(
        task=_job(task_status=status.value), upload_id="upload-1"
    )

    assert result.overall_status == status
    assert (result.docs_total, result.docs_indexed, result.docs_failed) == (
        1,
        docs_indexed,
        0,
    )


def test_single_pdf_upload_status_failed() -> None:
    """A failed single-PDF upload carries the job's error trace."""

    result = service._single_pdf_upload_status(
        task=_job(task_status=DocStatusEnum.failed.value, error_trace="500: boom"),
        upload_id="upload-1",
    )

    assert result.overall_status == DocStatusEnum.failed
    assert result.docs_failed == 1
    assert result.error_trace == "500: boom"


FINISHED = "2025-01-01T00:05:00+00:00"


@pytest.mark.parametrize(
    "statuses, overall, docs_indexed, docs_failed, error_prefix, finished",
    [
        (["success", "success"], "success", 2, 0, "", FINISHED),
        (["success", "in_progress"], "in_progress", 1, 0, "", None),
        (["success", "not_started"], "not_started", 1, 0, "", None),
        (["failed", "success"], "failed", 1, 1, "1 documents failed", FINISHED),
    ],
)
def test_zip_upload_status(
    statuses: list[str],
    overall: str,
    docs_indexed: int,
    docs_failed: int,
    error_prefix: str,
    finished: str | None,
) -> None:
    """Zip status precedence is failed > in progress > success > not started.

    Parameters
    ----------
    statuses
        `DocStatusEnum` member names, one per job.
    overall
        Expected overall status member name.
    docs_indexed
        Expected number of indexed documents.
    docs_failed
        Expected number of failed documents.
    error_prefix
        Expected start of the error trace.
    finished
        Expected finish time (ISO string) or `None`.
    """

    tasks = [
        _job(doc_name=f"{i}.pdf", task_status=DocStatusEnum[s].value)
        for i, s in enumerate(statuses)
    ]

    result = service._zip_upload_status(group=tasks, tasks=tasks, upload_id="u")

    assert result.overall_status == DocStatusEnum[overall]
    assert (result.docs_indexed, result.docs_failed) == (docs_indexed, docs_failed)
    assert result.error_trace is not None
    assert result.error_trace.startswith(error_prefix)
    expected_finished = datetime.fromisoformat(finished) if finished else None
    assert result.finished_datetime_utc == expected_finished


def test_zip_upload_status_truncates_failed_file_list() -> None:
    """Only the first three failed files are named in the error trace."""

    tasks = [
        _job(doc_name=f"{i}.pdf", task_status=DocStatusEnum.failed.value)
        for i in range(4)
    ]

    result = service._zip_upload_status(group=tasks, tasks=tasks, upload_id="u")

    assert result.error_trace == (
        "4 documents failed to ingest. Failed files: 0.pdf, 1.pdf, 2.pdf..."
    )
