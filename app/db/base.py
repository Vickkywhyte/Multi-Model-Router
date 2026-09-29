"""Declarative base for all SQLAlchemy ORM models.

All model modules import Base from here so that Alembic's autogenerate
can discover every table through Base.metadata.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
