from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Setting(BaseModel):
    __tablename__ = "settings"

    key = Column(String(100), unique=True, nullable=False, index=True)
    value_json = Column(Text, nullable=False)
    category = Column(String(50), default="general", nullable=False)
    is_editable = Column(Boolean, default=True, nullable=False)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    updater = relationship("User")


class MandatoryDocumentChecklist(BaseModel):
    __tablename__ = "mandatory_document_checklists"

    scheme_name = Column(String(100), nullable=False, index=True)
    document_type = Column(String(100), nullable=False, index=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)


class Holiday(BaseModel):
    __tablename__ = "holidays"

    holiday_date = Column(Date, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    state = Column(String(50), default="Karnataka", nullable=False)
    description = Column(Text, nullable=True)


class Job(BaseModel):
    __tablename__ = "jobs"

    job_type = Column(String(100), nullable=False, index=True)
    payload_json = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    progress = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    creator = relationship("User")


class SavedFilter(BaseModel):
    __tablename__ = "saved_filters"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # findings, cases, documents, etc.
    name = Column(String(100), nullable=False)
    filter_json = Column(Text, nullable=False)

    user = relationship("User")


class UserPreference(BaseModel):
    __tablename__ = "user_preferences"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    preference_key = Column(String(100), nullable=False, index=True)
    preference_value = Column(Text, nullable=False)

    user = relationship("User")
