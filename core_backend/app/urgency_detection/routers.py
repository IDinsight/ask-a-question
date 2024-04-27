from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import auth_bearer_token
from ..database import get_async_session
from ..urgency_rules.models import get_cosine_distances_from_rules
from ..utils import generate_secret_key
from .config import URGENCY_DETECTION_MAX_DISTANCE
from .models import save_urgency_query_to_db, save_urgency_response_to_db
from .schemas import UrgencyQuery, UrgencyResponse

router = APIRouter(
    dependencies=[Depends(auth_bearer_token)], tags=["Urgency Detection"]
)


@router.post("/urgency-detect", response_model=UrgencyResponse)
async def classify_text(
    urgency_query: UrgencyQuery, asession: AsyncSession = Depends(get_async_session)
) -> UrgencyResponse:
    """
    Classify the urgency of a text message
    """
    feedback_secret_key = generate_secret_key()
    urgency_query_db = await save_urgency_query_to_db(
        feedback_secret_key, urgency_query, asession
    )
    urgency_response = await cosine_distance_classifier(asession, urgency_query)

    await save_urgency_response_to_db(urgency_query_db, urgency_response, asession)

    return urgency_response


async def cosine_distance_classifier(
    asession: AsyncSession, urgency_query: UrgencyQuery
) -> UrgencyResponse:
    """
    Classify the urgency of a text message using cosine distance
    """

    cosine_distances = await get_cosine_distances_from_rules(
        asession, urgency_query.message_text
    )
    for _, rule in cosine_distances.items():
        if float(rule["distance"]) < float(URGENCY_DETECTION_MAX_DISTANCE):
            return UrgencyResponse(is_urgent=True, details=cosine_distances)

    return UrgencyResponse(
        is_urgent=False,
        details=cosine_distances,
    )
