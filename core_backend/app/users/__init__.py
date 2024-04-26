from datetime import datetime
from uuid import uuid4

from ..database import get_session
from ..utils import setup_logger
from .models import save_user_to_db_sync
from .schemas import UserCreate

logger = setup_logger()


hardcoded_users = [
    UserCreate(
        username="user1",
        user_id=uuid4().hex,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    ),
    UserCreate(
        username="user2",
        user_id=uuid4().hex,
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
