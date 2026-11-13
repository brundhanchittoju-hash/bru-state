import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ActivityLog(Base):
    """
    Append-only, cryptographically hash-chained activity log.
    Updates and deletions are strictly blocked at database and application level.
    """
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    sequence_id = Column(Integer, unique=True, nullable=False, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(150), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=True, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    actor = relationship("User", foreign_keys=[actor_id])
    case = relationship("AuditCase", foreign_keys=[case_id])
