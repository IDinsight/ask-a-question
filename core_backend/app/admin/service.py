"""This module contains the logic behind the admin (healthcheck) endpoints."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database_connection(*, asession: AsyncSession) -> str | None:
    """Check that the database is reachable by running a trivial query.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for the check.

    Returns
    -------
    str | None
        `None` if the database responded, otherwise the error message describing the
        failed connection. The error is returned rather than raised because the
        healthcheck reports failures with a custom response body.
    """

    try:
        await asession.execute(text("SELECT 1;"))
    except SQLAlchemyError as e:
        return f"Failed database connection: {e}"
    return None
