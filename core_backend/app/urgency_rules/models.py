from datetime import datetime
from typing import Dict, List, Optional, Union

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ..contents.config import PGVECTOR_VECTOR_SIZE
from ..models import Base, JSONDict
from ..utils import embedding
from .schemas import UrgencyRuleCreate


class UrgencyRuleDB(Base):
    """
    UrgencyRuleDB model class
    """

    __tablename__ = "urgency-rules"

    urgency_rule_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    urgency_rule_text: Mapped[str] = mapped_column(String, nullable=False)
    urgency_rule_vector: Mapped[Vector] = mapped_column(
        Vector(int(PGVECTOR_VECTOR_SIZE)), nullable=False
    )
    urgency_rule_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=True)
    created_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        """Pretty-print the UrgencyRuleDB object"""
        return f"<UrgencyRuleDB #{self.urgency_rule_id}: {self.urgency_rule_text})>"


async def save_urgency_rule_to_db(
    urgency_rule: UrgencyRuleCreate, asession: AsyncSession
) -> UrgencyRuleDB:
    """
    Save urgency rule to the database
    """
    urgency_rule_vector = await embedding(urgency_rule.urgency_rule_text)
    urgency_rule_db = UrgencyRuleDB(
        urgency_rule_text=urgency_rule.urgency_rule_text,
        urgency_rule_vector=urgency_rule_vector,
        urgency_rule_metadata=urgency_rule.urgency_rule_metadata,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )
    asession.add(urgency_rule_db)
    await asession.commit()
    await asession.refresh(urgency_rule_db)

    return urgency_rule_db


async def update_urgency_rule_in_db(
    urgency_rule_id: int, urgency_rule: UrgencyRuleCreate, asession: AsyncSession
) -> UrgencyRuleDB:
    """
    Update urgency rule in the database
    """
    urgency_rule_vector = await embedding(urgency_rule.urgency_rule_text)
    urgency_rule_db = UrgencyRuleDB(
        urgency_rule_id=urgency_rule_id,
        urgency_rule_text=urgency_rule.urgency_rule_text,
        urgency_rule_vector=urgency_rule_vector,
        urgency_rule_metadata=urgency_rule.urgency_rule_metadata,
        updated_datetime_utc=datetime.utcnow(),
    )
    urgency_rule_db = await asession.merge(urgency_rule_db)
    await asession.commit()
    await asession.refresh(urgency_rule_db)

    return urgency_rule_db


async def delete_urgency_rule_from_db(
    urgency_rule_id: int, asession: AsyncSession
) -> None:
    """
    Delete urgency rule from the database
    """
    stmt = delete(UrgencyRuleDB).where(UrgencyRuleDB.urgency_rule_id == urgency_rule_id)
    await asession.execute(stmt)
    await asession.commit()


async def get_urgency_rule_by_id_from_db(
    urgency_rule_id: int, asession: AsyncSession
) -> UrgencyRuleDB | None:
    """
    Get urgency rule by ID from the database
    """
    urgency_rule = await asession.get(UrgencyRuleDB, urgency_rule_id)
    return urgency_rule


async def get_urgency_rules_from_db(
    asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> List[UrgencyRuleDB]:
    """
    Get urgency rules from the database
    """
    stmt = select(UrgencyRuleDB).order_by(UrgencyRuleDB.urgency_rule_id)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    urgency_rules = (await asession.execute(stmt)).all()

    return [c[0] for c in urgency_rules] if urgency_rules else []


async def get_cosine_distances_from_rules(
    asession: AsyncSession,
    message_text: str,
) -> Dict[int, Dict[str, Union[str, float]]]:
    """
    Get cosine distances from urgency rules
    """
    message_vector = await embedding(message_text)
    query = select(
        UrgencyRuleDB,
        UrgencyRuleDB.urgency_rule_vector.cosine_distance(message_vector).label(
            "distance"
        ),
    ).order_by("distance")

    search_result = (await asession.execute(query)).all()

    results_dict = {}
    for i, r in enumerate(search_result):
        results_dict[i] = {
            "urgency_rule": r[0].urgency_rule_text,
            "distance": r[1],
        }

    return results_dict
