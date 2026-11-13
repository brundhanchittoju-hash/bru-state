import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String
from app.core.database import Base


def generate_uuid() -> str:
    """Generates a UUID4 string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin providing created_at, updated_at and deleted_at (soft delete)."""
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    def soft_delete(self):
        """Marks the record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)

    @property
    def is_deleted(self) -> bool:
        """Returns True if the record has been soft-deleted."""
        return self.deleted_at is not None


class BaseModel(Base, TimestampMixin):
    """Abstract base model with UUID primary key and timestamp/soft-delete mixin."""
    __abstract__ = True

    id = Column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        nullable=False,
    )
