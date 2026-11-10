"""Local fixtures for the docmuncher tests: an in-memory Redis and a PDF factory."""

import fnmatch
from io import BytesIO
from typing import Any, Callable, Optional

import pytest
from PyPDF2 import PdfWriter


class FakeRedis:
    """Tiny in-memory stand-in for the async Redis client used by docmuncher.

    Only the commands docmuncher calls are implemented. Values are stored as bytes,
    like the app's real client (created without `decode_responses=True`).
    """

    def __init__(self) -> None:
        """Start with an empty store."""

        self.store: dict[str, bytes] = {}
        self.expiry: dict[str, int] = {}

    async def get(self, key: str) -> Optional[bytes]:
        """Return the value stored at `key`, or `None`.

        Parameters
        ----------
        key
            The key to look up.

        Returns
        -------
        Optional[bytes]
            The stored value.
        """

        return self.store.get(key)

    async def set(
        self, key: str, value: Any, nx: bool = False, ex: Optional[int] = None
    ) -> Optional[bool]:
        """Store `value` at `key`, honouring the `nx` and `ex` options.

        Parameters
        ----------
        key
            The key to set.
        value
            The value; non-bytes values are stringified, as Redis does.
        nx
            Only set the key if it does not exist yet.
        ex
            Expiry in seconds (recorded, never enforced).

        Returns
        -------
        Optional[bool]
            `True` if the key was set, `None` if `nx` blocked it.
        """

        if nx and key in self.store:
            return None
        self.store[key] = value if isinstance(value, bytes) else str(value).encode()
        if ex is not None:
            self.expiry[key] = ex
        return True

    async def delete(self, key: str) -> int:
        """Delete `key`.

        Parameters
        ----------
        key
            The key to delete.

        Returns
        -------
        int
            The number of keys removed.
        """

        return 1 if self.store.pop(key, None) is not None else 0

    async def keys(self, pattern: str) -> list[bytes]:
        """Return the keys matching a glob `pattern`.

        Parameters
        ----------
        pattern
            Glob pattern, e.g. `docmuncher_job_*`.

        Returns
        -------
        list[bytes]
            The matching keys.
        """

        return [k.encode() for k in self.store if fnmatch.fnmatch(k, pattern)]

    async def mget(self, keys: list[bytes]) -> list[Optional[bytes]]:
        """Return the values for several keys.

        Parameters
        ----------
        keys
            The keys to fetch.

        Returns
        -------
        list[Optional[bytes]]
            The values, in key order.
        """

        return [self.store.get(k.decode()) for k in keys]


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Return an empty in-memory Redis.

    Returns
    -------
    FakeRedis
        The fake Redis client.
    """

    return FakeRedis()


@pytest.fixture(scope="session")
def make_pdf() -> Callable[[int], bytes]:
    """Return a factory that builds a blank PDF with a given number of pages.

    Returns
    -------
    Callable[[int], bytes]
        Factory taking the page count and returning the PDF bytes.
    """

    def _make_pdf(num_pages: int = 1) -> bytes:
        """Build a blank PDF.

        Parameters
        ----------
        num_pages
            Number of blank pages.

        Returns
        -------
        bytes
            The PDF file contents.
        """

        writer = PdfWriter()
        for _ in range(num_pages):
            writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)
        return buffer.getvalue()

    return _make_pdf
