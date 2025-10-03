"""
Base model with common fields for all database models
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UUIDMixin:
    """Mixin for UUID primary key"""

    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class BaseModel(TimestampMixin):
    """Base model combining common mixins"""

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self):
        """String representation"""
        attrs = ", ".join(
            f"{k}={v!r}"
            for k, v in self.to_dict().items()
            if not k.startswith("_")
        )
        return f"<{self.__class__.__name__}({attrs})>"
