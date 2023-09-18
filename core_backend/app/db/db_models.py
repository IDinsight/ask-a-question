from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""

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

    feedback = relationship("Feedback", back_populates="query", lazy=True)

    def __repr__(self):
        """Pretty Print"""
        return f"<Query #{self.inbound_id}> {self.query_text}>"


class Feedback(Base):
    """
    SQLAlchemy data model for feedback provided by user
    """

    __tablename__ = "feedback"

    feedback_id = Column(Integer, primary_key=True, index=True, nullable=False)
    query_id = Column(Integer, ForeignKey("user-queries.query_id"))
    feedback_text = Column(String, nullable=False)
    feedback_datetime_utc = Column(DateTime, nullable=False)

    query = relationship("UserQuery", back_populates="feedback", lazy=True)

    def __repr__(self):
        """Pretty Print"""
        return (
            f"<Feedback #{self.feedback_id} for query "
            f"#{self.query_id}> {self.feedback_text}>"
        )
