from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VerificationRule(BaseModel):
    __tablename__ = "verification_rules"

    rule_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    scheme = Column(String(100), nullable=True, index=True)
    severity = Column(String(50), default="medium", nullable=False)  # low, medium, high, critical
    is_enabled = Column(Boolean, default=True, nullable=False)
    parameters_json = Column(Text, nullable=True)

    history = relationship("RuleSettingsHistory", back_populates="rule", cascade="all, delete-orphan")
    runs = relationship("RuleRun", back_populates="rule", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="rule")


class RuleSettingsHistory(BaseModel):
    __tablename__ = "rule_settings_history"

    rule_id = Column(String(36), ForeignKey("verification_rules.id"), nullable=False, index=True)
    old_parameters = Column(Text, nullable=True)
    new_parameters = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    rule = relationship("VerificationRule", back_populates="history")
    user = relationship("User")


class RuleRun(BaseModel):
    __tablename__ = "rule_runs"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("verification_rules.id"), nullable=False, index=True)
    run_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    triggered_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="completed", nullable=False)
    items_evaluated = Column(Integer, default=0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    thresholds_snapshot_json = Column(Text, nullable=True)
    execution_summary_json = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0, nullable=False)

    case = relationship("AuditCase", back_populates="rule_runs")
    rule = relationship("VerificationRule", back_populates="runs")
    trigger_user = relationship("User")
