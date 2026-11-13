from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    document_type = Column(String(100), nullable=True, index=True)
    status = Column(String(50), default="uploaded", nullable=False, index=True)  # uploaded, processing, processed, failed
    page_count = Column(Integer, default=0, nullable=False)
    current_version = Column(Integer, default=1, nullable=False)
    processing_error = Column(Text, nullable=True)
    classification_confidence = Column(Float, default=0.0, nullable=False)
    classification_keywords = Column(Text, nullable=True)
    extractor_used = Column(String(50), nullable=True)
    document_date = Column(DateTime(timezone=True), nullable=True)
    uploader_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    case = relationship("AuditCase", back_populates="documents")
    uploader = relationship("User")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    annotations = relationship("DocumentAnnotation", back_populates="document", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(BaseModel):
    __tablename__ = "document_versions"

    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    stored_filename = Column(String(255), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)
    document_type = Column(String(100), nullable=True)
    classification_confidence = Column(Float, default=0.0, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    document = relationship("Document", back_populates="versions")
    creator = relationship("User")


class DocumentAnnotation(BaseModel):
    __tablename__ = "document_annotations"

    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    page = Column(Integer, nullable=False)
    bbox = Column(Text, nullable=True)  # JSON "[x0, y0, x1, y1]"
    note = Column(Text, nullable=False)
    finding_id = Column(String(36), nullable=True, index=True)  # Nullable link for Phase 4
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    document = relationship("Document", back_populates="annotations")
    creator = relationship("User")


class ExtractedField(BaseModel):
    __tablename__ = "extracted_fields"

    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    original_text = Column(Text, nullable=True)
    extracted_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    is_overridden = Column(Boolean, default=False, nullable=False)
    overridden_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    override_comment = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    source_page = Column(Integer, default=1, nullable=False)
    bbox = Column(Text, nullable=True)  # "[x0, y0, x1, y1]" normalized
    extractor = Column(String(50), default="text_layer", nullable=False)  # "text_layer" | "ocr" | "rule_parser" | "llm" | "manual"
    validation_status = Column(String(20), default="not_checked", nullable=False)  # "valid" | "invalid" | "not_checked"
    validation_message = Column(Text, nullable=True)
    extracted_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    document = relationship("Document", back_populates="extracted_fields")
    overrider = relationship("User")
