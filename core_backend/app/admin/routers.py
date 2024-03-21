from urllib.parse import urlparse

from aiohttp.client_exceptions import ClientConnectorError
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ALIGN_SCORE_API, ALIGN_SCORE_METHOD
from ..database import get_async_session
from ..utils import get_http_client

router = APIRouter()


@router.get("/healthcheck")
async def healthcheck(
    db_session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """
    Healthcheck endpoint - checks connection to Db
    """
    try:
        await db_session.execute(text("SELECT 1;"))
    except SQLAlchemyError as e:
        return JSONResponse(
            status_code=500, content={"message": f"Failed database connection: {e}"}
        )

    if ALIGN_SCORE_METHOD == "AlignScore":
        url = urlparse(ALIGN_SCORE_API)
        healthcheck_url = f"{url.scheme!r}://{url.netloc!r}/healthcheck"
        http_client = get_http_client()
        try:
            resp = await http_client.get(healthcheck_url)
        except ClientConnectorError as e:
            return JSONResponse(
                status_code=500,
                content={
                    "message": (
                        "Failed to connect to alignScore "
                        f"container at: {healthcheck_url}."
                        f" Error: {e}"
                    )
                },
            )
        if resp.status != 200:
            return JSONResponse(
                status_code=500,
                content={
                    "message": (
                        "Response is not 200 from alignScore "
                        f"healthcheck at: {healthcheck_url}"
                    )
                },
            )

    return JSONResponse(status_code=200, content={"status": "ok"})
