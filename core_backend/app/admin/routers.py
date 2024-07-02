from dataclasses import dataclass
from urllib.parse import urlparse

from aiohttp.client_exceptions import ClientConnectorError
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ALIGN_SCORE_API, ALIGN_SCORE_METHOD, LITELLM_ENDPOINT
from ..database import get_async_session
from ..utils import get_http_client

router = APIRouter()


@dataclass
class dependent_service:
    """Dataclass for service to healthcheck"""

    name: str
    healthcheck_url: str


services = [
    dependent_service(
        name="litellm_proxy", healthcheck_url=LITELLM_ENDPOINT + "/health/liveliness"
    )
]

if ALIGN_SCORE_METHOD == "AlignScore":
    url = urlparse(ALIGN_SCORE_API)
    services.append(
        dependent_service(
            name="alignScore",
            healthcheck_url=f"{url.scheme!r}://{url.netloc!r}/healthcheck",
        )
    )


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

    http_client = get_http_client()
    for service in services:
        try:
            resp = await http_client.get(service.healthcheck_url)
        except ClientConnectorError as e:
            return JSONResponse(
                status_code=500,
                content={
                    "message": (
                        f"Failed to connect to {service.name} "
                        f"at: {service.healthcheck_url}."
                        f" Error: {e}"
                    )
                },
            )
        if resp.status != 200:
            return JSONResponse(
                status_code=500,
                content={
                    "message": (
                        f"Response is not 200 from {service.name} "
                        f"healthcheck at: {service.healthcheck_url}"
                    )
                },
            )

    return JSONResponse(status_code=200, content={"status": "ok"})
