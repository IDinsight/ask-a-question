"""HTTP tests for the docmuncher endpoints.

Authorisation and filename checks run against the real service (they only need
the users created by the shared fixtures). Job creation, PDF processing and job
status are mocked at `app.docmuncher.router.service`, so no PDF is parsed and no
OCR or LLM call is made.
"""

from datetime import datetime, timezone
from typing import Any, Mapping
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import ForbiddenError, NotFoundError
from app.docmuncher.schemas import (
    DocIngestionStatusZip,
    DocStatusEnum,
    DocUploadResponsePdf,
    DocUploadResponseZip,
)
from app.docmuncher.service import PdfIngestionJob
from tests.conftest import TEST_WORKSPACE_NAME_1

NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)
SERVICE = "app.docmuncher.router.service"


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


def _auth(token: str) -> dict[str, str]:
    """Build a bearer authorization header.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    dict[str, str]
        The request headers.
    """

    return {"Authorization": f"Bearer {token}"}


def _pdf_task(doc_name: str, task_id: str) -> DocUploadResponsePdf:
    """Build an upload response entry for one PDF.

    Parameters
    ----------
    doc_name
        The PDF name.
    task_id
        The job's Redis key.

    Returns
    -------
    DocUploadResponsePdf
        The upload response entry.
    """

    return DocUploadResponsePdf(
        upload_id="upload-1",
        user_id=1,
        workspace_id=1,
        created_datetime_utc=NOW,
        task_id=task_id,
        doc_name=doc_name,
    )


def _ingestion_job(file_name: str, task_id: str) -> PdfIngestionJob:
    """Build a background ingestion job.

    Parameters
    ----------
    file_name
        The PDF name.
    task_id
        The job's Redis key.

    Returns
    -------
    PdfIngestionJob
        The job.
    """

    return PdfIngestionJob(
        task_id=task_id,
        file_name=file_name,
        content=b"%PDF",
        workspace_id=1,
        asession=MagicMock(),
    )


@pytest.fixture
def process_pdf_file(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace the background PDF processing task with a recording mock.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    AsyncMock
        The mocked `process_pdf_file`.
    """

    mock = AsyncMock()
    monkeypatch.setattr(f"{SERVICE}.process_pdf_file", mock)
    return mock


@pytest.mark.parametrize(
    "method, path",
    [
        ("post", "/docmuncher/upload"),
        ("get", "/docmuncher/status/is_job_running"),
        ("get", "/docmuncher/status/data"),
    ],
)
def test_endpoints_require_login(client: TestClient, method: str, path: str) -> None:
    """Every docmuncher endpoint rejects anonymous requests.

    Parameters
    ----------
    client
        The test client.
    method
        The HTTP method.
    path
        The endpoint path.
    """

    response = client.request(method, path)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_requires_file(client: TestClient, access_token_admin_1: str) -> None:
    """A request without a file fails validation.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    """

    response = client.post("/docmuncher/upload", headers=_auth(access_token_admin_1))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_forbidden_for_read_only_user(
    client: TestClient, access_token_read_only_1: str, process_pdf_file: AsyncMock
) -> None:
    """Read-only users cannot ingest documents.

    Parameters
    ----------
    client
        The test client.
    access_token_read_only_1
        Read-only token for workspace 1.
    process_pdf_file
        The mocked background task.
    """

    response = client.post(
        "/docmuncher/upload",
        files={"file": ("guide.pdf", b"%PDF", "application/pdf")},
        headers=_auth(access_token_read_only_1),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "User does not have the required role to ingest documents."
    }
    process_pdf_file.assert_not_awaited()


def test_upload_rejects_unsupported_file_type(
    client: TestClient, access_token_admin_1: str, process_pdf_file: AsyncMock
) -> None:
    """Files that are not .pdf or .zip are rejected before being read.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    process_pdf_file
        The mocked background task.
    """

    response = client.post(
        "/docmuncher/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=_auth(access_token_admin_1),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": "Only PDF files are supported for document ingestion."
    }
    process_pdf_file.assert_not_awaited()


def test_upload_pdf_schedules_job(
    client: TestClient,
    access_token_admin_1: str,
    monkeypatch: pytest.MonkeyPatch,
    process_pdf_file: AsyncMock,
) -> None:
    """A PDF upload returns its job and runs it as a background task.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    monkeypatch
        Pytest monkeypatch fixture.
    process_pdf_file
        The mocked background task.
    """

    task = _pdf_task("guide.pdf", "docmuncher_job_1")
    job = _ingestion_job("guide.pdf", "docmuncher_job_1")
    create_jobs = AsyncMock(return_value=(task, [job]))
    monkeypatch.setattr(f"{SERVICE}.create_ingestion_jobs", create_jobs)

    response = client.post(
        "/docmuncher/upload",
        files={"file": ("guide.pdf", b"%PDF-bytes", "application/pdf")},
        headers=_auth(access_token_admin_1),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["task_id"] == "docmuncher_job_1"
    assert body["doc_name"] == "guide.pdf"
    assert body["task_status"] == DocStatusEnum.not_started.value
    # The router hands the raw upload to the service.
    create_kwargs = _await_kwargs(create_jobs)
    assert create_kwargs["file_content"] == b"%PDF-bytes"
    assert create_kwargs["filename"] == "guide.pdf"
    assert create_kwargs["workspace_db"].workspace_name == TEST_WORKSPACE_NAME_1
    # TestClient runs background tasks before returning the response.
    process_pdf_file.assert_awaited_once()
    process_kwargs = _await_kwargs(process_pdf_file)
    assert process_kwargs["task_id"] == job.task_id
    assert process_kwargs["file_name"] == job.file_name
    assert process_kwargs["content"] == job.content
    assert process_kwargs["workspace_id"] == job.workspace_id
    assert process_kwargs["asession"] is job.asession
    assert process_kwargs["redis"] is client.app.state.redis  # type: ignore[attr-defined]


def test_upload_zip_schedules_one_job_per_pdf(
    client: TestClient,
    access_token_admin_1: str,
    monkeypatch: pytest.MonkeyPatch,
    process_pdf_file: AsyncMock,
) -> None:
    """A zip upload returns the zip summary and schedules every PDF job.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    monkeypatch
        Pytest monkeypatch fixture.
    process_pdf_file
        The mocked background task.
    """

    names = ["a.pdf", "b.pdf"]
    zip_response = DocUploadResponseZip(
        upload_id="upload-1",
        user_id=1,
        workspace_id=1,
        parent_file_name="bundle.zip",
        created_datetime_utc=NOW,
        tasks=[_pdf_task(n, f"job_{n}") for n in names],
        docs_total=2,
    )
    jobs = [_ingestion_job(n, f"job_{n}") for n in names]
    monkeypatch.setattr(
        f"{SERVICE}.create_ingestion_jobs",
        AsyncMock(return_value=(zip_response, jobs)),
    )

    response = client.post(
        "/docmuncher/upload",
        files={"file": ("bundle.zip", b"PK", "application/zip")},
        headers=_auth(access_token_admin_1),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["docs_total"] == 2
    assert body["parent_file_name"] == "bundle.zip"
    assert [t["doc_name"] for t in body["tasks"]] == names
    assert [c.kwargs["file_name"] for c in process_pdf_file.await_args_list] == names


def test_upload_quota_error_is_forbidden(
    client: TestClient,
    access_token_admin_1: str,
    monkeypatch: pytest.MonkeyPatch,
    process_pdf_file: AsyncMock,
) -> None:
    """A quota error from the service becomes a 403 and schedules nothing.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    monkeypatch
        Pytest monkeypatch fixture.
    process_pdf_file
        The mocked background task.
    """

    monkeypatch.setattr(
        f"{SERVICE}.create_ingestion_jobs",
        AsyncMock(side_effect=ForbiddenError("Document ingestion exceeds quota")),
    )

    response = client.post(
        "/docmuncher/upload",
        files={"file": ("guide.pdf", b"%PDF", "application/pdf")},
        headers=_auth(access_token_admin_1),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Document ingestion exceeds quota"}
    process_pdf_file.assert_not_awaited()


@pytest.mark.parametrize("running", [True, False])
def test_is_job_running(
    client: TestClient,
    access_token_admin_1: str,
    monkeypatch: pytest.MonkeyPatch,
    running: bool,
) -> None:
    """The endpoint returns the service's boolean for the caller's workspace.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    monkeypatch
        Pytest monkeypatch fixture.
    running
        The value returned by the service.
    """

    is_job_running = AsyncMock(return_value=running)
    monkeypatch.setattr(f"{SERVICE}.is_job_running", is_job_running)

    response = client.get(
        "/docmuncher/status/is_job_running", headers=_auth(access_token_admin_1)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() is running
    kwargs = _await_kwargs(is_job_running)
    assert kwargs["workspace_name"] == TEST_WORKSPACE_NAME_1
    assert kwargs["redis"] is client.app.state.redis  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "path", ["/docmuncher/status/is_job_running", "/docmuncher/status/data"]
)
def test_job_status_forbidden_for_read_only_user(
    client: TestClient, access_token_read_only_1: str, path: str
) -> None:
    """Read-only users cannot see ingestion status.

    Parameters
    ----------
    client
        The test client.
    access_token_read_only_1
        Read-only token for workspace 1.
    path
        The endpoint path.
    """

    response = client.get(path, headers=_auth(access_token_read_only_1))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "User does not have the required role to request ingestion status."
    }


def test_get_all_jobs(
    client: TestClient, access_token_admin_1: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The endpoint returns one status entry per upload.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    upload_status = DocIngestionStatusZip(
        upload_id="upload-1",
        user_id=1,
        workspace_id=1,
        parent_file_name="guide.pdf",
        created_datetime_utc=NOW,
        overall_status=DocStatusEnum.success,
        docs_indexed=1,
        docs_failed=0,
        docs_total=1,
    )
    get_all_jobs = AsyncMock(return_value=[upload_status])
    monkeypatch.setattr(f"{SERVICE}.get_all_jobs", get_all_jobs)

    response = client.get(
        "/docmuncher/status/data", headers=_auth(access_token_admin_1)
    )

    assert response.status_code == status.HTTP_200_OK
    body: list[dict[str, Any]] = response.json()
    assert len(body) == 1
    assert body[0]["upload_id"] == "upload-1"
    assert body[0]["overall_status"] == DocStatusEnum.success.value
    assert (body[0]["docs_indexed"], body[0]["docs_total"]) == (1, 1)
    assert _await_kwargs(get_all_jobs)["workspace_name"] == TEST_WORKSPACE_NAME_1


def test_get_all_jobs_not_found(
    client: TestClient, access_token_admin_1: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing-jobs error from the service becomes a 404.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        Admin token for workspace 1.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr(
        f"{SERVICE}.get_all_jobs", AsyncMock(side_effect=NotFoundError("No jobs found"))
    )

    response = client.get(
        "/docmuncher/status/data", headers=_auth(access_token_admin_1)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "No jobs found"}
