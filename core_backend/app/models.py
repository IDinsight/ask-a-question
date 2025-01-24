"""This module contains the base class for SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase

JSONDict = dict[str, str]


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass
