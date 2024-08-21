"""This script is useful if you want to test the dashboard with dummy data. Navigate to
the core_backend directory of the project and run the following command:
    > python add_dummy_data_to_db.py
"""

import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

# Append the framework path. NB: This is required if this script is invoked from the
# command line. However, it is not necessary if it is imported from a pip install.
if __name__ == "__main__":
    PACKAGE_PATH = str(Path(__file__).resolve())
    PACKAGE_PATH_SPLIT = PACKAGE_PATH.split(os.path.join("scripts"))
    PACKAGE_PATH = PACKAGE_PATH_SPLIT[0]
    if PACKAGE_PATH not in sys.path:
        print(f"Appending '{PACKAGE_PATH}' to system path...")
        sys.path.append(PACKAGE_PATH)


from app.config import PGVECTOR_VECTOR_SIZE
from app.contents.models import ContentDB
from app.database import get_session
from app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    ResponseFeedbackDB,
)
from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB

# admin user (first user is admin)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "fullaccess")
_USER_ID = 1

N_DATAPOINTS = 100
URGENCY_RATE = 0.1
NEGATIVE_FEEDBACK_RATE = 0.1


def add_year_data() -> None:
    """Add N_DATAPOINTS of data for each day in the past year."""

    now = datetime.now(timezone.utc)
    last_year = now - timedelta(days=365)
    year_datetimes = [
        last_year + timedelta(days=i)
        for i in random.choices(range(365), k=N_DATAPOINTS)
    ]

    for dt in year_datetimes:
        create_data(dt)


def add_month_data() -> None:
    """Add N_DATAPOINTS of data for each hour in the past month."""

    now = datetime.now(timezone.utc)
    last_month = now - timedelta(days=30)
    month_datetimes = [
        last_month + timedelta(days=i) + timedelta(hours=random.randint(0, 24))
        for i in random.choices(range(30), k=N_DATAPOINTS)
    ]

    for dt in month_datetimes:
        create_data(dt)


def add_week_data() -> None:
    """Add N_DATAPOINTS of data for each hour in the past week."""

    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)
    week_datetimes = [
        last_week + timedelta(days=i) + timedelta(hours=random.randint(0, 24))
        for i in random.choices(range(7), k=N_DATAPOINTS)
    ]

    for dt in week_datetimes:
        create_data(dt)


def add_day_data() -> None:
    """Add N_DATAPOINTS of data for each hour in the past day."""

    now = datetime.now(timezone.utc)
    last_day = now - timedelta(hours=24)
    hour_datetimes = [
        last_day + timedelta(hours=i) for i in random.choices(range(24), k=N_DATAPOINTS)
    ]

    for dt in hour_datetimes:
        create_data(dt)


def create_data(dt: datetime) -> None:
    """Create a record for a given datetime.

    Parameters
    ----------
    dt
        The datetime for which to create a record.
    """

    is_urgent = random.random() < URGENCY_RATE
    session = next(get_session())
    create_urgency_record(dt, is_urgent, session)
    if not is_urgent:
        query_db = create_query_record(dt, session)
        query_id = query_db.query_id
        session_id = query_db.session_id
        response_feedback_is_negative = random.random() < NEGATIVE_FEEDBACK_RATE
        create_response_feedback_record(
            dt=dt,
            query_id=query_id,
            session_id=session_id,
            is_negative=response_feedback_is_negative,
            session=session,
        )
        content_feedback_is_negative = random.random() < NEGATIVE_FEEDBACK_RATE
        create_content_feedback_record(
            dt=dt,
            query_id=query_id,
            session_id=session_id,
            is_negative=content_feedback_is_negative,
            session=session,
        )
    session.close()


def create_urgency_record(dt: datetime, is_urgent: bool, session: Session) -> None:
    """Create an urgency record for a given datetime.

    Parameters
    ----------
    dt
        The datetime for which to create a record.
    is_urgent
        Specifies whether the record is urgent.
    session
        `Session` object for database transactions.
    """

    urgency_db = UrgencyQueryDB(
        user_id=_USER_ID,
        message_text="test message",
        message_datetime_utc=dt,
        feedback_secret_key="abc123",  # pragma: allowlist secret
    )
    session.add(urgency_db)
    session.commit()
    urgency_response = UrgencyResponseDB(
        is_urgent=is_urgent,
        details={"details": "test details"},
        query_id=urgency_db.urgency_query_id,
        user_id=_USER_ID,
        response_datetime_utc=dt,
    )
    session.add(urgency_response)
    session.commit()


def create_query_record(dt: datetime, session: Session) -> QueryDB:
    """Create a query record for a given datetime.

    Parameters
    ----------
    dt
        The datetime for which to create a record.
    session
        `Session` object for database transactions.

    Returns
    -------
    QueryDB
        The query record.
    """

    query_db = QueryDB(
        user_id=_USER_ID,
        session_id=1,
        feedback_secret_key="abc123",  # pragma: allowlist secret
        query_text="test query",
        query_generate_llm_response=False,
        query_metadata={},
        query_datetime_utc=dt,
    )
    session.add(query_db)
    session.commit()
    return query_db


def create_response_feedback_record(
    dt: datetime, query_id: int, session_id: int, is_negative: bool, session: Session
) -> None:
    """Create a feedback record for a given datetime.

    Parameters
    ----------
    dt
        The datetime for which to create a record.
    query_id
        The ID of the query record.
    is_negative
        Specifies whether the feedback is negative.
    session
        `Session` object for database transactions.
    """

    sentiment = "negative" if is_negative else "positive"
    feedback_db = ResponseFeedbackDB(
        feedback_datetime_utc=dt,
        query_id=query_id,
        user_id=_USER_ID,
        session_id=session_id,
        feedback_sentiment=sentiment,
    )
    session.add(feedback_db)
    session.commit()


def create_content_feedback_record(
    dt: datetime,
    query_id: int,
    session_id: int,
    is_negative: bool,
    session: Session,
) -> None:
    """Create a content feedback record for a given datetime.

    Parameters
    ----------
    dt
        The datetime for which to create a record.
    query_id
        The ID of the query record.
    is_negative
        Specifies whether the content feedback is negative.
    session
        `Session` object for database transactions.
    """

    sentiment = "negative" if is_negative else "positive"
    all_content_ids = [c.content_id for c in session.query(ContentDB).all()]
    content_ids = random.choices(all_content_ids, k=3)
    for content_id in content_ids:
        feedback_db = ContentFeedbackDB(
            feedback_datetime_utc=dt,
            query_id=query_id,
            user_id=_USER_ID,
            session_id=session_id,
            content_id=content_id,
            feedback_sentiment=sentiment,
        )
        session.add(feedback_db)
        session.commit()


def add_content_data() -> None:
    """Add N_DATAPOINTS of content data to the database."""

    content = [
        "Ways to manage back pain during pregnancy",
        "Headache during pregnancy is normal ‚except after 20 weeks",
        "Yes, pregnancy can cause TOOTHACHE",
        "Ways to manage HEARTBURN in pregnancy",
        "Some LEG cramps are normal during pregnancy",
    ]

    for i, c in enumerate(content):
        session = next(get_session())
        query_count = np.random.randint(100, 700)
        positive_votes = np.random.randint(0, query_count)
        negative_votes = np.random.randint(0, query_count - positive_votes)
        content_db = ContentDB(
            user_id=_USER_ID,
            content_embedding=np.random.rand(int(PGVECTOR_VECTOR_SIZE))
            .astype(np.float32)
            .tolist(),
            content_title=c,
            content_text=f"Test content #{i}",
            content_metadata={},
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            query_count=query_count,
            positive_votes=positive_votes,
            negative_votes=negative_votes,
            is_archived=False,
        )
        session.add(content_db)
        session.commit()
        session.close()


if __name__ == "__main__":
    add_content_data()
    add_year_data()
    add_month_data()
    add_week_data()
    add_day_data()
    print("Added dummy data to DB")
