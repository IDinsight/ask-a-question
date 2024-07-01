from fastapi import APIRouter, Depends

from ..auth.dependencies import authenticate_key
from ..utils import setup_logger

logger = setup_logger()

router = APIRouter(dependencies=[Depends(authenticate_key)], tags=["Voice API"])
