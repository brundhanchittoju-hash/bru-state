from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Report(BaseModel):
    __tablename__ = "reports"

    report_number = Column(String(50), unique=True, index=True, nullable=True)
    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    report_title = Column(String(255), nullable=False)
    report_type = Column(String(50), default="preliminary", nullable=False)
    current_version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="Draft", nullable=False)  # Draft, Final, Approved, Superseded
    generated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_comment = Column(Text, nullable=True)

    case = relationship("AuditCase", back_populates="reports")
    generator = relationship("User", foreign_keys=[generated_by])
    approver = relationship("User", foreign_keys=[approved_by])
    versions = relationship("ReportVersion", back_populates="report", cascade="all, delete-orphan", order_by="desc(ReportVersion.version_number)")


class ReportVersion(BaseModel):
    __tablename__ = "report_versions"

    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="Draft", nullable=False)  # Draft, Final, Approved, Superseded
    file_path = Column(String(500), nullable=True)
    pdf_storage_path = Column(String(500), nullable=True)  # legacy synonym preserved
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    pdf_sha256 = Column(String(64), nullable=True, index=True)
    snapshot_json = Column(Text, nullable=True)
    includes_demo_watermark = Column(Boolean, default=True, nullable=False)
    qr_verification_code = Column(String(500), nullable=True)
    generated_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    generated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    approved_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_comment = Column(Text, nullable=True)

    report = relationship("Report", back_populates="versions")
    generator = relationship("User", foreign_keys=[generated_by_id])
    approver = relationship("User", foreign_keys=[approved_by_id])
