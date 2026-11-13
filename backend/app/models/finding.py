from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Finding(BaseModel):
    __tablename__ = "findings"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("verification_rules.id"), nullable=True, index=True)
    finding_number = Column(String(50), nullable=True, index=True)  # e.g. F-2025-0001
    fingerprint = Column(String(64), nullable=True, index=True)
    category = Column(String(100), default="financial", nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    calculation = Column(Text, nullable=True)
    risk_level = Column(String(50), default="medium", nullable=False, index=True)  # low, medium, high, critical
    status = Column(
        String(50),
        default="Open",
        nullable=False,
        index=True,
    )  # Open, Under Review, Confirmed, Dismissed, Escalated, Auto-resolved (condition no longer detected)
    financial_implication = Column(Numeric(14, 2), default=0.0, nullable=False)
    amount_at_risk = Column(Numeric(14, 2), default=0.0, nullable=False)
    confidence = Column(Float, default=100.0, nullable=False)
    inputs_used_json = Column(Text, nullable=True)
    thresholds_used_json = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)
    data_changed_since_review = Column(Boolean, default=False, nullable=False)
    assigned_auditor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    auto_resolved_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("AuditCase", back_populates="findings")
    rule = relationship("VerificationRule", back_populates="findings")
    assigned_auditor = relationship("User", foreign_keys=[assigned_auditor_id])
    evidence = relationship("FindingEvidence", back_populates="finding", cascade="all, delete-orphan")
    reviews = relationship("FindingReview", back_populates="finding", cascade="all, delete-orphan")
    notes = relationship("FindingNote", back_populates="finding", cascade="all, delete-orphan")
    clarifications = relationship("FindingClarification", back_populates="finding", cascade="all, delete-orphan")


class FindingEvidence(BaseModel):
    __tablename__ = "finding_evidence"

    finding_id = Column(String(36), ForeignKey("findings.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True, index=True)
    page_number = Column(Integer, nullable=True)
    excerpt = Column(Text, nullable=True)

    finding = relationship("Finding", back_populates="evidence")
    document = relationship("Document")
    transaction = relationship("Transaction")


class FindingReview(BaseModel):
    __tablename__ = "finding_reviews"

    finding_id = Column(String(36), ForeignKey("findings.id"), nullable=False, index=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewer_role = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)  # reviewed, escalated, approved, closed
    comments = Column(Text, nullable=False)

    finding = relationship("Finding", back_populates="reviews")
    reviewer = relationship("User")
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)


class FindingNote(BaseModel):
    __tablename__ = "finding_notes"

    finding_id = Column(String(36), ForeignKey("findings.id"), nullable=False, index=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("finding_notes.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)

    finding = relationship("Finding", back_populates="notes")
    author = relationship("User")
    parent = relationship("FindingNote", remote_side="FindingNote.id", backref="replies")


class FindingClarification(BaseModel):
    __tablename__ = "finding_clarifications"

    finding_id = Column(String(36), ForeignKey("findings.id"), nullable=False, index=True)
    requested_by_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    responded_by_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    response = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, answered
    responded_at = Column(DateTime(timezone=True), nullable=True)

    finding = relationship("Finding", back_populates="clarifications")
    requester = relationship("User", foreign_keys=[requested_by_id])
    responder = relationship("User", foreign_keys=[responded_by_id])
