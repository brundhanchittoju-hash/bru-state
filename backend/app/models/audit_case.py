from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AuditCase(BaseModel):
    __tablename__ = "audit_cases"

    case_number = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    financial_year = Column(String(20), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    taluk = Column(String(100), nullable=True, index=True)
    gram_panchayat = Column(String(150), nullable=True)
    scheme_name = Column(String(100), nullable=True, index=True)
    audit_type = Column(String(50), default="Statutory", nullable=False)
    project_name = Column(String(255), nullable=True)
    estimated_cost = Column(Numeric(14, 2), nullable=True)
    actual_expenditure = Column(Numeric(14, 2), nullable=True)
    sanctioned_amount = Column(Numeric(14, 2), nullable=True)
    planned_start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    priority = Column(String(20), default="medium", nullable=False, index=True)
    remarks = Column(Text, nullable=True)
    lead_auditor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(50), default="draft", nullable=False, index=True)
    risk_level = Column(String(50), default="low", nullable=False, index=True)
    scope_notes = Column(Text, nullable=True)

    department = relationship("Department")
    lead_auditor = relationship("User", foreign_keys=[lead_auditor_id])
    status_history = relationship("CaseStatusHistory", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="case", cascade="all, delete-orphan")
    financial_records = relationship("FinancialRecord", back_populates="case", cascade="all, delete-orphan")
    record_links = relationship("RecordLink", back_populates="case", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="case", cascade="all, delete-orphan")
    rule_runs = relationship("RuleRun", back_populates="case", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="case", cascade="all, delete-orphan")
    versions = relationship("CaseVersion", back_populates="case", cascade="all, delete-orphan")
    scheduled_events = relationship("ScheduledEvent", back_populates="case", cascade="all, delete-orphan")


class CaseStatusHistory(BaseModel):
    __tablename__ = "case_status_history"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)

    case = relationship("AuditCase", back_populates="status_history")
    user = relationship("User")


class CaseVersion(BaseModel):
    __tablename__ = "case_versions"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    reopened_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reopen_reason = Column(Text, nullable=False)
    snapshot_json = Column(Text, nullable=True)

    case = relationship("AuditCase", back_populates="versions")
    reopened_by = relationship("User")


class ScheduledEvent(BaseModel):
    __tablename__ = "scheduled_events"

    title = Column(String(200), nullable=False)
    event_date = Column(Date, nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=True, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), default="audit_deadline", nullable=False)  # audit_deadline, hearing, submission, review

    case = relationship("AuditCase", back_populates="scheduled_events")
    creator = relationship("User")
