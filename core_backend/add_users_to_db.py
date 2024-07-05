import os
from datetime import datetime

from app.database import get_session
from app.users.models import UserDB
from app.utils import get_key_hash, get_password_salted_hash, setup_logger
from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

logger = setup_logger()

# admin user (first user is admin)
USER1_USERNAME = os.environ.get("USER1_USERNAME", "admin")
USER1_PASSWORD = os.environ.get("USER1_PASSWORD", "fullaccess")
USER1_API_KEY = os.environ.get("USER1_API_KEY", "admin-key")
USER1_CONTENT_QUOTA = os.environ.get("USER1_CONTENT_QUOTA", None)

user_db = UserDB(
    username=USER1_USERNAME,
    hashed_password=get_password_salted_hash(USER1_PASSWORD),
    hashed_api_key=get_key_hash(USER1_API_KEY),
    content_quota=USER1_CONTENT_QUOTA,
    created_datetime_utc=datetime.utcnow(),
    updated_datetime_utc=datetime.utcnow(),
)

if __name__ == "__main__":
    db_session = next(get_session())
    stmt = select(UserDB).where(UserDB.username == user_db.username)
    result = db_session.execute(stmt)
    try:
        result.one()
        logger.info(f"User with username {user_db.username} already exists.")
    except NoResultFound:
        db_session.add(user_db)
        logger.info(f"User with username {user_db.username} added to local database.")
    except MultipleResultsFound:
        logger.error(
            "Multiple users with username "
            f"{user_db.username} found in local database."
        )

    db_session.commit()
    db_session.close()
