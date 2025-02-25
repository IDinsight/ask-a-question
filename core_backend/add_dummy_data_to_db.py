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
    PACKAGE_PATH_ROOT = str(Path(__file__).resolve())
    PACKAGE_PATH_SPLIT = PACKAGE_PATH_ROOT.split(os.path.join("core_backend"))
    PACKAGE_PATH = Path(PACKAGE_PATH_SPLIT[0]) / "core_backend"
    if PACKAGE_PATH not in sys.path:
        print(f"Appending '{PACKAGE_PATH}' to system path...")
        sys.path.append(str(PACKAGE_PATH))


from app.config import PGVECTOR_VECTOR_SIZE
from app.contents.models import ContentDB
from app.database import get_session
from app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    QueryResponseContentDB,
    ResponseFeedbackDB,
)
from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB

# Admin user (first user is admin).
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "fullaccess")

_WORKSPACE_ID = 1
N_DATAPOINTS = 2000
NEGATIVE_FEEDBACK_RATE = 0.1
URGENCY_RATE = 0.1


def add_year_data() -> None:
    """Add `N_DATAPOINTS` of data for each day in the past year."""

    now = datetime.now(timezone.utc)
    last_year = now - timedelta(days=365)
    year_datetimes = [
        last_year + timedelta(days=i)
        for i in random.choices(range(365), k=N_DATAPOINTS)
    ]

    for dt in year_datetimes:
        create_data(dt)


def add_month_data() -> None:
    """Add `N_DATAPOINTS` of data for each hour in the past month."""

    now = datetime.now(timezone.utc)
    last_month = now - timedelta(days=30)
    month_datetimes = [
        last_month + timedelta(days=i) + timedelta(hours=random.randint(0, 24))
        for i in random.choices(range(30), k=N_DATAPOINTS)
    ]

    for dt in month_datetimes:
        create_data(dt)


def add_week_data() -> None:
    """Add `N_DATAPOINTS` of data for each hour in the past week."""

    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)
    week_datetimes = [
        last_week + timedelta(days=i) + timedelta(hours=random.randint(0, 24))
        for i in random.choices(range(7), k=N_DATAPOINTS)
    ]

    for dt in week_datetimes:
        create_data(dt)


def add_day_data() -> None:
    """Add `N_DATAPOINTS` of data for each hour in the past day."""

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
        create_content_for_query(dt=dt, query_id=query_id, session=session)
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
        feedback_secret_key="abc123",  # pragma: allowlist secret
        message_datetime_utc=dt,
        message_text="test message",
        workspace_id=_WORKSPACE_ID,
    )
    session.add(urgency_db)
    session.commit()
    urgency_response = UrgencyResponseDB(
        details={"details": "test details"},
        is_urgent=is_urgent,
        query_id=urgency_db.urgency_query_id,
        response_datetime_utc=dt,
        workspace_id=_WORKSPACE_ID,
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
        feedback_secret_key="abc123",  # pragma: allowlist secret
        query_datetime_utc=dt,
        query_generate_llm_response=False,
        query_metadata={},
        query_text=generate_synthetic_query(),
        session_id=1,
        workspace_id=_WORKSPACE_ID,
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
    session_id
        The ID of the session record.
    is_negative
        Specifies whether the feedback is negative.
    session
        `Session` object for database transactions.
    """

    sentiment = "negative" if is_negative else "positive"
    feedback_db = ResponseFeedbackDB(
        feedback_datetime_utc=dt,
        feedback_sentiment=sentiment,
        query_id=query_id,
        session_id=session_id,
        workspace_id=_WORKSPACE_ID,
    )
    session.add(feedback_db)
    session.commit()


POSITIVE_FEEDBACK_TEXTS = ["Great!", "Very helpful!", "Thanks!"]
NEGATIVE_FEEDBACK_TEXTS = ["Not helpful", "Confusing", "Too long"]


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
    session_id
        The ID of the session record.
    is_negative
        Specifies whether the content feedback is negative.
    session
        `Session` object for database transactions.
    """

    sentiment = "negative" if is_negative else "positive"
    sentiment_text = (
        random.choice(NEGATIVE_FEEDBACK_TEXTS)
        if is_negative
        else random.choice(POSITIVE_FEEDBACK_TEXTS)
    )
    all_content_ids = [c.content_id for c in session.query(ContentDB).all()]
    content_ids = random.choices(all_content_ids, k=3)
    for content_id in content_ids:
        feedback_db = ContentFeedbackDB(
            content_id=content_id,
            feedback_datetime_utc=dt,
            feedback_sentiment=sentiment,
            feedback_text=sentiment_text,
            query_id=query_id,
            session_id=session_id,
            workspace_id=_WORKSPACE_ID,
        )
        session.add(feedback_db)
        session.commit()


def create_content_for_query(dt: datetime, query_id: int, session: Session) -> None:
    """Create a `QueryResponseContentDB` record for a given `datetime` and `query_id`.

    Parameters
    ----------
    dt
        The datetime for which to create a record.
    query_id
        The ID of the query record.
    session
        `Session` object for database transactions.
    """

    all_content_ids = [c.content_id for c in session.query(ContentDB).all()]
    content_ids = random.choices(
        all_content_ids,
        weights=[c.query_count for c in session.query(ContentDB).all()],
        k=8,
    )
    for content_id in content_ids:
        response_db = QueryResponseContentDB(
            content_id=content_id,
            created_datetime_utc=dt,
            query_id=query_id,
            workspace_id=_WORKSPACE_ID,
        )
        session.add(response_db)
        session.commit()


def add_content_data() -> None:
    """Add `N_DATAPOINTS` of content data to the database."""

    content = [
        "Ways to manage back pain during pregnancy",
        "Headache during pregnancy is normal ‚except after 20 weeks",
        "Yes, pregnancy can cause TOOTHACHE",
        "Ways to manage HEARTBURN in pregnancy",
        "Some LEG cramps are normal during pregnancy",
        "How to handle swollen FEET",
        "Managing GAS and bloating during pregnancy",
        "Yes, pregnancy can affect your BREATHING",
        "Snack often to prevent DIZZINESS",
        "FAINTING could mean anemia – visit the clinic to find out",
    ]

    for i, c in enumerate(content):
        session = next(get_session())
        query_count = np.random.randint(100, 700)
        positive_votes = np.random.randint(0, query_count)
        negative_votes = np.random.randint(0, query_count - positive_votes)
        content_db = ContentDB(
            content_embedding=np.random.rand(int(PGVECTOR_VECTOR_SIZE))
            .astype(np.float32)
            .tolist(),
            content_metadata={},
            content_text=f"Test content #{i}",
            content_title=c,
            created_datetime_utc=datetime.now(timezone.utc),
            is_archived=False,
            negative_votes=negative_votes,
            positive_votes=positive_votes,
            query_count=query_count,
            updated_datetime_utc=datetime.now(timezone.utc),
            workspace_id=_WORKSPACE_ID,
        )
        session.add(content_db)
        session.commit()
        session.close()


MATERNAL_HEALTH_TERMS = [
    # General Terms
    "pregnancy",
    "birth",
    "postpartum",
    "natal care",
    "breastfeeding",
    "midwife",
    "maternal health",
    "childbirth",
    "labor",
    "delivery",
    "newborn",
    "baby",
    "preterm birth",
    "gestational diabetes",
    "ultrasound",
    "fetal monitoring",
    "prenatal care",
    "maternity leave",
    "family planning",
    # Medical Conditions
    "preeclampsia",
    "eclampsia",
    "placenta previa",
    "placental abruption",
    "hyperemesis gravidarum",
    "chorioamnionitis",
    "amniotic fluid embolism",
    "postpartum hemorrhage",
    "polyhydramnios",
    "oligohydramnios",
    "intrauterine growth restriction",
    "stillbirth",
    "hemolytic disease",
    # Procedures and Tests
    "amniocentesis",
    "chorionic villus sampling",
    "non-stress test",
    "biophysical profile",
    "doppler ultrasound",
    "glucose tolerance test",
    "cervical check",
    "internal fetal monitoring",
    # Support and Care
    "lactation consultant",
    "doula",
    "support group",
    "parenting classes",
    "infant care",
    "postpartum support",
    "mental health screening",
    "breastfeeding support",
    "pediatric care",
    # Wellness and Lifestyle
    "nutrition during pregnancy",
    "exercise during pregnancy",
    "birth plan",
    "home birth",
    "hospital birth",
    "water birth",
    "natural birth",
    "epidural",
    "pain management",
    "birthing center",
    # Emotional and Psychological Aspects
    "postpartum depression",
    "anxiety",
    "parenting stress",
    "bonding with baby",
    "maternal bonding",
    "new parent support",
    "adjustment to parenthood",
    "family dynamics",
]

# Common query templates
QUERY_TEMPLATES = [
    "What are the symptoms of {term}?",
    "How can I manage {term} during pregnancy?",
    "What is {term} and how does it affect childbirth?",
    "Where can I find support for {term}?",
    "What are the latest treatments for {term}?",
    "Is {term} common during pregnancy?",
    "How does {term} impact postpartum recovery?",
    "What should I know about {term} before giving birth?",
    "Can {term} affect my baby’s health?",
    "What are the best practices for dealing with {term}?",
]


def generate_synthetic_query() -> str:
    """Generate a random human-like query related to maternal health.

    Returns
    -------
    str
        The synthetic query.
    """

    template = random.choice(QUERY_TEMPLATES)
    term = random.choice(MATERNAL_HEALTH_TERMS)
    return template.format(term=term)


if __name__ == "__main__":
    add_content_data()
    add_year_data()
    add_month_data()
    add_week_data()
    add_day_data()
    print("Added dummy data to DB")
