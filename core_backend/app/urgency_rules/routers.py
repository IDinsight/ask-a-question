from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_fullaccess_user
from ..auth.schemas import AuthenticatedUser
from ..database import get_async_session
from ..utils import setup_logger
from .models import (
    UrgencyRuleDB,
    delete_urgency_rule_from_db,
    get_urgency_rule_by_id_from_db,
    get_urgency_rules_from_db,
    save_urgency_rule_to_db,
    update_urgency_rule_in_db,
)
from .schemas import UrgencyRuleCreate, UrgencyRuleRetrieve

router = APIRouter(prefix="/urgency_rules", tags=["Urgency Rules"])
logger = setup_logger(__name__)


@router.post("/", response_model=UrgencyRuleRetrieve)
async def create_urgency_rule(
    urgency_rule: UrgencyRuleCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> UrgencyRuleRetrieve:
    """
    Create a new urgency rule
    """
    urgency_rule_db = await save_urgency_rule_to_db(urgency_rule, asession)
    return _convert_record_to_schema(urgency_rule_db)


@router.get("/{urgency_rule_id}", response_model=UrgencyRuleRetrieve)
async def get_urgency_rule(
    urgency_rule_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> UrgencyRuleRetrieve:
    """
    Get a single urgency rule by id
    """

    urgency_rule_db = await get_urgency_rule_by_id_from_db(urgency_rule_id, asession)
    return _convert_record_to_schema(urgency_rule_db)


@router.delete("/{urgency_rule_id}")
async def delete_urgency_rule(
    urgency_rule_id: int,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete a single urgency rule by id
    """

    await delete_urgency_rule_from_db(urgency_rule_id, asession)


@router.put("/{urgency_rule_id}", response_model=UrgencyRuleRetrieve)
async def update_urgency_rule(
    urgency_rule_id: int,
    urgency_rule: UrgencyRuleCreate,
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> UrgencyRuleRetrieve:
    """
    Update a single urgency rule by id
    """
    old_content = await get_urgency_rule_by_id_from_db(
        urgency_rule_id,
        asession,
    )

    if not old_content:
        raise HTTPException(
            status_code=404, detail=f"Urgency Rule id `{urgency_rule_id}` not found"
        )

    urgency_rule_db = await update_urgency_rule_in_db(
        urgency_rule_id, urgency_rule, asession
    )
    return _convert_record_to_schema(urgency_rule_db)


@router.get("/", response_model=list[UrgencyRuleRetrieve])
async def get_urgency_rules(
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UrgencyRuleRetrieve]:
    """
    Get all urgency rules
    """
    urgency_rules_db = await get_urgency_rules_from_db(asession)
    return [
        _convert_record_to_schema(urgency_rule_db)
        for urgency_rule_db in urgency_rules_db
    ]


def _convert_record_to_schema(urgency_rule_db: UrgencyRuleDB) -> UrgencyRuleRetrieve:
    """
    Convert a UrgencyRuleDB record to a UrgencyRuleRetrieve schema
    """
    return UrgencyRuleRetrieve(
        urgency_rule_id=urgency_rule_db.id,
        created_datetime_utc=urgency_rule_db.created_datetime_utc,
        updated_datetime_utc=urgency_rule_db.updated_datetime_utc,
        urgency_rule_text=urgency_rule_db.urgency_rule_text,
        urgency_rule_metadata=urgency_rule_db.urgency_rule_metadata,
    )
