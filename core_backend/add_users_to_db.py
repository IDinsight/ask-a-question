from datetime import datetime
from uuid import uuid4

from app.auth.config import USER1_USERNAME, USER2_USERNAME
from app.database import get_session
from app.users.models import UserDB
from app.utils import setup_logger
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

logger = setup_logger()

user_dbs = [
    UserDB(
        username=USER1_USERNAME,
        user_id=uuid4().hex,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    ),
    UserDB(
        username=USER2_USERNAME,
        user_id=uuid4().hex,
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
            result.scalar_one()
            logger.info(f"User with username {user_db.username} already exists.")
        except NoResultFound:
            db_session.add(user_db)
            logger.info(
                f"User with username {user_db.username} added to local database."
            )
    db_session.commit()
    db_session.close()
