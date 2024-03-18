from typing import Dict

from sqlalchemy.orm import DeclarativeBase

JSONDict = Dict[str, str]


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""

    pass
