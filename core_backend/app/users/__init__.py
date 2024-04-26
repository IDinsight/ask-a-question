from datetime import datetime
from uuid import uuid4

from ..auth.config import (
    USER1_RETRIEVAL_SECRET,
    USER1_USERNAME,
    USER2_RETRIEVAL_SECRET,
    USER2_USERNAME,
)
from ..database import get_session
from ..utils import setup_logger
from .models import save_user_to_db_sync
from .schemas import UserCreate

logger = setup_logger()


hardcoded_users = [
    UserCreate(
        username=USER1_USERNAME,
        user_id=uuid4().hex,
        retrieval_token=USER1_RETRIEVAL_SECRET,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    ),
    UserCreate(
        username=USER2_USERNAME,
        user_id=uuid4().hex,
        retrieval_token=USER2_RETRIEVAL_SECRET,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    ),
]


session = next(get_session())
for user in hardcoded_users:
    try:
        save_user_to_db_sync(user, session)
    except Exception as e:
        logger.error(f"An error occurred while adding user: {e}")
