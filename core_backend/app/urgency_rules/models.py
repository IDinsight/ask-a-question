"""This module contains the ORM for managing urgency detection rules in the
`UrgencyRuleDB` database and functions for interacting with the database.
"""

from datetime import datetime, timezone
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ..config import PGVECTOR_VECTOR_SIZE
from ..models import Base, JSONDict
from ..utils import embedding
from .schemas import UrgencyRuleCosineDistance, UrgencyRuleCreate


class UrgencyRuleDB(Base):
    """ORM for managing urgency detection rules.

    This database ties into the Admin app and allows the user to view, add, edit,
    and delete content in the `urgency_rule` table.
    """

    __tablename__ = "urgency_rule"

    urgency_rule_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    urgency_rule_text: Mapped[str] = mapped_column(String, nullable=False)
    urgency_rule_vector: Mapped[Vector] = mapped_column(
        Vector(int(PGVECTOR_VECTOR_SIZE)), nullable=False
    )
    urgency_rule_metadata: Mapped[JSONDict] = mapped_column(JSON, nullable=True)
    created_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        """Construct the string representation of the `UrgencyRuleDB` object.

        Returns
        -------
        str
            A string representation of the `UrgencyRuleDB` object.
        """

        return f"<UrgencyRuleDB #{self.urgency_rule_id}: {self.urgency_rule_text})>"


async def save_urgency_rule_to_db(
    user_id: int, urgency_rule: UrgencyRuleCreate, asession: AsyncSession
) -> UrgencyRuleDB:
    """Save urgency rule to the database.

    Parameters
    ----------
    user_id
        The ID of the user who created the urgency rule.
    urgency_rule
        The urgency rule to save to the database.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    UrgencyRuleDB
        The urgency rule object saved to the database.
    """

    metadata = {
        "trace_user_id": "user_id-" + str(user_id),
        "generation_name": "save_urgency_rule_to_db",
    }
    urgency_rule_vector = await embedding(
        urgency_rule.urgency_rule_text, metadata=metadata
    )
    urgency_rule_db = UrgencyRuleDB(
        user_id=user_id,
        urgency_rule_text=urgency_rule.urgency_rule_text,
        urgency_rule_vector=urgency_rule_vector,
        urgency_rule_metadata=urgency_rule.urgency_rule_metadata,
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    asession.add(urgency_rule_db)
    await asession.commit()
    await asession.refresh(urgency_rule_db)

    return urgency_rule_db


async def update_urgency_rule_in_db(
    user_id: int,
    urgency_rule_id: int,
    urgency_rule: UrgencyRuleCreate,
    asession: AsyncSession,
) -> UrgencyRuleDB:
    """Update urgency rule in the database.

    Parameters
    ----------
    user_id
        The ID of the user who updated the urgency rule.
    urgency_rule_id
        The ID of the urgency rule to update.
    urgency_rule
        The urgency rule to update.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    UrgencyRuleDB
        The updated urgency rule object
    """

    metadata = {
        "trace_user_id": "user_id-" + str(user_id),
        "generation_name": "update_urgency_rule_in_db",
    }
    urgency_rule_vector = await embedding(
        urgency_rule.urgency_rule_text, metadata=metadata
    )
    urgency_rule_db = UrgencyRuleDB(
        urgency_rule_id=urgency_rule_id,
        user_id=user_id,
        urgency_rule_text=urgency_rule.urgency_rule_text,
        urgency_rule_vector=urgency_rule_vector,
        urgency_rule_metadata=urgency_rule.urgency_rule_metadata,
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    urgency_rule_db = await asession.merge(urgency_rule_db)
    await asession.commit()
    await asession.refresh(urgency_rule_db)

    return urgency_rule_db


async def delete_urgency_rule_from_db(
    user_id: int, urgency_rule_id: int, asession: AsyncSession
) -> None:
    """Delete urgency rule from the database.

    Parameters
    ----------
    user_id
        The ID of the user requesting to delete the urgency rule.
    urgency_rule_id
        The ID of the urgency rule to delete.
    asession
        `AsyncSession` object for database transactions.
    """

    stmt = (
        delete(UrgencyRuleDB)
        .where(UrgencyRuleDB.user_id == user_id)
        .where(UrgencyRuleDB.urgency_rule_id == urgency_rule_id)
    )
    await asession.execute(stmt)
    await asession.commit()


async def get_urgency_rule_by_id_from_db(
    user_id: int, urgency_rule_id: int, asession: AsyncSession
) -> UrgencyRuleDB | None:
    """Get urgency rule by ID from the database.

    Parameters
    ----------
    user_id
        The ID of the user requesting the urgency rule.
    urgency_rule_id
        The ID of the urgency rule to retrieve.
    asession
        `AsyncSession` object for database

    Returns
    -------
    UrgencyRuleDB | None
        The urgency rule object if it exists, otherwise `None`.
    """

    stmt = (
        select(UrgencyRuleDB)
        .where(UrgencyRuleDB.user_id == user_id)
        .where(UrgencyRuleDB.urgency_rule_id == urgency_rule_id)
    )
    urgency_rule_row = (await asession.execute(stmt)).first()
    return urgency_rule_row[0] if urgency_rule_row else None


async def get_urgency_rules_from_db(
    user_id: int, asession: AsyncSession, offset: int = 0, limit: Optional[int] = None
) -> list[UrgencyRuleDB]:
    """Get urgency rules from the database.

    Parameters
    ----------
    user_id
        The ID of the user requesting the urgency rules.
    asession
        `AsyncSession` object for database transactions.
    offset
        The number of urgency rule items to skip.
    limit
        The maximum number of urgency rule items to retrieve. If not specified, then
        all urgency rule items are retrieved.

    Returns
    -------
    List[UrgencyRuleDB]
        The list of urgency rules in the database.
    """

    stmt = (
        select(UrgencyRuleDB)
        .where(UrgencyRuleDB.user_id == user_id)
        .order_by(UrgencyRuleDB.urgency_rule_id)
    )
    if offset > 0:
        stmt = stmt.offset(offset)
    if isinstance(limit, int) and limit > 0:
        stmt = stmt.limit(limit)
    urgency_rules = (await asession.execute(stmt)).all()

    return [c[0] for c in urgency_rules] if urgency_rules else []


async def get_cosine_distances_from_rules(
    user_id: int,
    message_text: str,
    asession: AsyncSession,
) -> dict[int, UrgencyRuleCosineDistance]:
    """Get cosine distances from urgency rules.

    Parameters
    ----------
    user_id
        The ID of the user requesting the cosine distances from the urgency rules.
    message_text
        The message text to compare against the urgency rules.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    Dict[int, UrgencyRuleCosineDistance]
        The dictionary of urgency rules and their cosine distances from `message_text`.
    """

    metadata = {
        "trace_user_id": "user_id-" + str(user_id),
        "generation_name": "get_cosine_distances_from_rules",
    }
    message_vector = await embedding(message_text, metadata=metadata)
    query = (
        select(
            UrgencyRuleDB,
            UrgencyRuleDB.urgency_rule_vector.cosine_distance(message_vector).label(
                "distance"
            ),
        )
        .where(UrgencyRuleDB.user_id == user_id)
        .order_by("distance")
    )

    search_result = (await asession.execute(query)).all()

    results_dict = {}
    for i, r in enumerate(search_result):
        results_dict[i] = UrgencyRuleCosineDistance(
            urgency_rule=r[0].urgency_rule_text,
            distance=r[1],
        )

    return results_dict
