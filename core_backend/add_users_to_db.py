import os
from datetime import datetime

from app.database import get_session
from app.users.models import UserDB
from app.utils import get_key_hash, get_password_salted_hash, setup_logger
from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

logger = setup_logger()

# user 1
USER1_USERNAME = os.environ.get("USER1_USERNAME", "user1")
USER1_PASSWORD = os.environ.get("USER1_PASSWORD", "fullaccess")
USER1_RETRIEVAL_KEY = os.environ.get("USER1_RETRIEVAL_KEY", "user1-key")

# user 2
USER2_USERNAME = os.environ.get("USER2_USERNAME", "user2")
USER2_PASSWORD = os.environ.get("USER2_PASSWORD", "fullaccess")
USER2_RETRIEVAL_KEY = os.environ.get("USER2_RETRIEVAL_KEY", "user2-key")


user_dbs = [
    UserDB(
        username=USER1_USERNAME,
        hashed_password=get_password_salted_hash(USER1_PASSWORD),
        hashed_retrieval_key=get_key_hash(USER1_RETRIEVAL_KEY),
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    ),
    UserDB(
        username=USER2_USERNAME,
        hashed_password=get_password_salted_hash(USER2_PASSWORD),
        hashed_retrieval_key=get_key_hash(USER2_RETRIEVAL_KEY),
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    ),
]


if __name__ == "__main__":
    db_session = next(get_session())
    for user_db in user_dbs:
        stmt = select(UserDB).where(UserDB.username == user_db.username)
        result = db_session.execute(stmt)
        try:
            result.one()
            logger.info(f"User with username {user_db.username} already exists.")
        except NoResultFound:
            db_session.add(user_db)
            logger.info(
                f"User with username {user_db.username} added to local database."
            )
        except MultipleResultsFound:
            logger.error(
                "Multiple users with username "
                f"{user_db.username} found in local database."
            )

    db_session.commit()
    db_session.close()
