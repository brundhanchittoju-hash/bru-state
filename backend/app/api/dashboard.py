from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase, ScheduledEvent
from app.models.audit_trail import ActivityLog
from app.models.document import Document
from app.models.finding import Finding
from app.models.rules import VerificationRule
from app.models.user import User
from app.services.audit_trail import log_activity

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ==============================================================================
# Schemas
# ==============================================================================

class DashboardStatsOut(BaseModel):
    total_cases: int
    open_cases: int
    completed_cases: int
    documents_uploaded: int
    documents_processed: int
    pending_findings: int
    high_risk_findings: int
    medium_risk_findings: int
    low_risk_findings: int
    critical_risk_findings: int
    r001_duplicate_payments: int
    r003_amount_mismatches: int
    r008_missing_documents: int
    pending_approvals_count: int
    total_flagged_amount: float


class PriorityFindingOut(BaseModel):
    id: str
    finding_number: str
    title: str
    case_id: str
    case_number: Optional[str] = None
    district: Optional[str] = None
    scheme: Optional[str] = None
    rule_code: Optional[str] = None
    risk_score: float
    severity: str
    amount: float
    status: str
    created_at: datetime


class RecentActivityOut(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    actor_name: str
    created_at: datetime
    payload_summary: Optional[str] = None


class ScheduledEventIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    event_date: date
    case_id: Optional[str] = None
    description: Optional[str] = None
    event_type: str = Field(default="audit_deadline")  # audit_deadline, hearing, submission, review


class ScheduledEventOut(BaseModel):
    id: str
    title: str
    event_date: date
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    created_by_name: str
    description: Optional[str] = None
    event_type: str
    created_at: datetime


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(
    financial_year: Optional[str] = None,
    district: Optional[str] = None,
    department_id: Optional[str] = None,
    assigned_only: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes all 12 live KPIs directly from the SQL database with optional filters.
    """
    # 1. Base Case Query
    case_q = db.query(AuditCase).filter(AuditCase.deleted_at.is_(None))
    if financial_year:
        case_q = case_q.filter(AuditCase.financial_year == financial_year)
    if district:
        case_q = case_q.filter(AuditCase.district == district)
    if department_id:
        case_q = case_q.filter(AuditCase.department_id == department_id)
    if assigned_only:
        case_q = case_q.filter(AuditCase.lead_auditor_id == current_user.id)

    case_ids_subquery = case_q.with_entities(AuditCase.id).subquery()

    total_cases = case_q.count()
    open_cases = case_q.filter(~func.lower(AuditCase.status).in_(["approved", "closed"])).count()
    completed_cases = case_q.filter(func.lower(AuditCase.status).in_(["approved", "closed"])).count()

    # 2. Document Queries
    doc_q = db.query(Document).filter(
        Document.deleted_at.is_(None),
        Document.case_id.in_(case_ids_subquery),
    )
    documents_uploaded = doc_q.count()
    documents_processed = doc_q.filter(func.lower(Document.status) == "processed").count()

    # 3. Finding Queries
    find_q = db.query(Finding).filter(
        Finding.deleted_at.is_(None),
        Finding.case_id.in_(case_ids_subquery),
    )
    pending_findings = find_q.filter(
        func.lower(Finding.status).in_(["open", "escalated", "needs_clarification", "pending_approval"])
    ).count()

    high_risk_findings = find_q.filter(func.lower(Finding.risk_level) == "high").count()
    medium_risk_findings = find_q.filter(func.lower(Finding.risk_level) == "medium").count()
    low_risk_findings = find_q.filter(func.lower(Finding.risk_level) == "low").count()
    critical_risk_findings = find_q.filter(func.lower(Finding.risk_level) == "critical").count()

    # Rule-specific findings (join with VerificationRule)
    r001_duplicate = (
        find_q.join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(VerificationRule.rule_code == "R-001")
        .count()
    )
    r003_mismatches = (
        find_q.join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(VerificationRule.rule_code == "R-003")
        .count()
    )
    r008_missing = (
        find_q.join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(VerificationRule.rule_code == "R-008")
        .count()
    )

    pending_approvals = find_q.filter(func.lower(Finding.status).in_(["pending_approval", "pending approval"])).count()

    flagged_amt_res = find_q.with_entities(func.sum(Finding.amount_at_risk)).scalar()
    total_flagged_amount = float(flagged_amt_res or 0.0)

    return DashboardStatsOut(
        total_cases=total_cases,
        open_cases=open_cases,
        completed_cases=completed_cases,
        documents_uploaded=documents_uploaded,
        documents_processed=documents_processed,
        pending_findings=pending_findings,
        high_risk_findings=high_risk_findings,
        medium_risk_findings=medium_risk_findings,
        low_risk_findings=low_risk_findings,
        critical_risk_findings=critical_risk_findings,
        r001_duplicate_payments=r001_duplicate,
        r003_amount_mismatches=r003_mismatches,
        r008_missing_documents=r008_missing,
        pending_approvals_count=pending_approvals,
        total_flagged_amount=round(total_flagged_amount, 2),
    )


@router.get("/priority-queue", response_model=List[PriorityFindingOut])
def get_priority_queue(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns top open findings sorted by risk score descending."""
    findings = (
        db.query(Finding)
        .filter(
            Finding.deleted_at.is_(None),
            func.lower(Finding.status).in_(["open", "escalated", "needs_clarification", "pending_approval", "needs clarification", "pending approval"]),
        )
        .order_by(Finding.amount_at_risk.desc())
        .limit(limit)
        .all()
    )

    results = []
    for f in findings:
        case = f.case
        results.append(
            PriorityFindingOut(
                id=f.id,
                finding_number=f.finding_number or f.id[:8],
                title=f.title,
                case_id=f.case_id,
                case_number=case.case_number if case else None,
                district=case.district if case else None,
                scheme=case.scheme_name if case else None,
                rule_code=f.rule.rule_code if f.rule else None,
                risk_score=float(f.confidence or 0.0),
                severity=f.risk_level,
                amount=float(f.amount_at_risk or 0.0),
                status=f.status,
                created_at=f.created_at,
            )
        )
    return results


@router.get("/recent-activity", response_model=List[RecentActivityOut])
def get_recent_activity(
    limit: int = 15,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns recent activity logs with actor information."""
    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )

    out = []
    for l in logs:
        summary = None
        if l.payload_json:
            summary = f"Ref: {l.entity_type} {l.entity_id or ''}"
        out.append(
            RecentActivityOut(
                id=l.id,
                action=l.action,
                entity_type=l.entity_type,
                entity_id=l.entity_id,
                actor_name=l.actor_name or "System",
                created_at=l.created_at,
                payload_summary=summary,
            )
        )
    return out


@router.get("/calendar", response_model=List[ScheduledEventOut])
def list_calendar_events(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    case_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists audit calendar deadlines and events."""
    q = db.query(ScheduledEvent).filter(ScheduledEvent.deleted_at.is_(None))
    if start_date:
        q = q.filter(ScheduledEvent.event_date >= start_date)
    if end_date:
        q = q.filter(ScheduledEvent.event_date <= end_date)
    if case_id:
        q = q.filter(ScheduledEvent.case_id == case_id)

    events = q.order_by(ScheduledEvent.event_date.asc()).all()
    out = []
    for e in events:
        out.append(
            ScheduledEventOut(
                id=e.id,
                title=e.title,
                event_date=e.event_date,
                case_id=e.case_id,
                case_number=e.case.case_number if e.case else None,
                created_by_name=e.creator.full_name if e.creator else "System",
                description=e.description,
                event_type=e.event_type,
                created_at=e.created_at,
            )
        )
    return out


@router.post("/calendar", response_model=ScheduledEventOut, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    payload: ScheduledEventIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Creates a new scheduled event or statutory audit deadline."""
    if payload.case_id:
        c = db.query(AuditCase).filter(AuditCase.id == payload.case_id, AuditCase.deleted_at.is_(None)).first()
        if not c:
            raise HTTPException(status_code=404, detail="Specified audit case not found")

    ev = ScheduledEvent(
        title=payload.title,
        event_date=payload.event_date,
        case_id=payload.case_id,
        created_by_id=current_user.id,
        description=payload.description,
        event_type=payload.event_type,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CALENDAR_EVENT_CREATED",
        entity_type="scheduled_event",
        entity_id=ev.id,
        case_id=ev.case_id,
        payload={"title": ev.title, "event_date": str(ev.event_date), "type": ev.event_type},
    )

    return ScheduledEventOut(
        id=ev.id,
        title=ev.title,
        event_date=ev.event_date,
        case_id=ev.case_id,
        case_number=ev.case.case_number if ev.case else None,
        created_by_name=current_user.full_name,
        description=ev.description,
        event_type=ev.event_type,
        created_at=ev.created_at,
    )


@router.delete("/calendar/{event_id}")
def delete_calendar_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Soft-deletes a scheduled calendar event."""
    ev = db.query(ScheduledEvent).filter(ScheduledEvent.id == event_id, ScheduledEvent.deleted_at.is_(None)).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Scheduled event not found")

    ev.deleted_at = datetime.utcnow()
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CALENDAR_EVENT_DELETED",
        entity_type="scheduled_event",
        entity_id=ev.id,
        case_id=ev.case_id,
        payload={"title": ev.title},
    )

    return {"message": "Calendar event removed successfully", "id": event_id}
