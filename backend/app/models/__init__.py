from sqlalchemy import event
from app.core.database import Base
from app.models.base import BaseModel
from app.models.user import Role, Department, User
from app.models.audit_case import AuditCase, CaseStatusHistory, CaseVersion, ScheduledEvent
from app.models.document import Document, DocumentVersion, DocumentAnnotation, ExtractedField
from app.models.financial import Vendor, VendorAlias, Transaction, FinancialRecord, RecordLink
from app.models.rules import VerificationRule, RuleSettingsHistory, RuleRun
from app.models.finding import Finding, FindingEvidence, FindingReview, FindingNote, FindingClarification
from app.models.report import Report, ReportVersion
from app.models.audit_trail import ActivityLog
from app.models.system import Setting, MandatoryDocumentChecklist, Holiday, Job, SavedFilter, UserPreference


# Guard against UPDATE or DELETE on ActivityLog
@event.listens_for(ActivityLog, "before_update")
def prevent_activity_log_update(mapper, connection, target):
    raise ValueError("ActivityLog is strictly append-only: updates are prohibited.")


@event.listens_for(ActivityLog, "before_delete")
def prevent_activity_log_delete(mapper, connection, target):
    raise ValueError("ActivityLog is strictly append-only: deletions are prohibited.")


__all__ = [
    "Base",
    "BaseModel",
    "Role",
    "Department",
    "User",
    "AuditCase",
    "CaseStatusHistory",
    "CaseVersion",
    "ScheduledEvent",
    "Document",
    "DocumentVersion",
    "DocumentAnnotation",
    "ExtractedField",
    "Vendor",
    "VendorAlias",
    "Transaction",
    "FinancialRecord",
    "RecordLink",
    "VerificationRule",
    "RuleSettingsHistory",
    "RuleRun",
    "Finding",
    "FindingEvidence",
    "FindingReview",
    "FindingNote",
    "FindingClarification",
    "Report",
    "ReportVersion",
    "ActivityLog",
    "Setting",
    "MandatoryDocumentChecklist",
    "Holiday",
    "Job",
    "SavedFilter",
    "UserPreference",
]
