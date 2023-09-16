from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class UserQuery(Base):
    """
    SQLAlchemy data model for questions asked by user
    """

    __tablename__ = "user-queries"

    query_id = Column(Integer, primary_key=True, index=True, nullable=False)
    feedback_secret_key = Column(String, nullable=False)
    query_text = Column(String, nullable=False)
    query_metadata = Column(JSON, nullable=False)
    query_datetime_utc = Column(DateTime, nullable=False)

    def __repr__(self):
        """Pretty Print"""
        return f"<Query #{self.inbound_id}> {self.query_text}>"
