import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase, CaseStatusHistory, CaseVersion
from app.models.document import Document, ExtractedField
from app.models.finding import Finding
from app.models.rules import RuleRun
from app.models.user import Department, User
from app.services.audit_trail import log_activity

router = APIRouter(prefix="/cases", tags=["Audit Cases"])

VALID_TRANSITIONS: Dict[str, List[str]] = {
    "draft": ["documents_uploaded", "closed"],
    "documents_uploaded": ["processing", "draft", "closed"],
    "processing": ["verification", "documents_uploaded", "closed"],
    "verification": ["review", "processing", "closed"],
    "review": ["approved", "verification", "closed"],
    "approved": ["closed"],
    "closed": [],  # Can only be reopened via /cases/{id}/reopen
}


# ==============================================================================
# Schemas
# ==============================================================================

class CaseCreateIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    financial_year: str = Field(default="2024-25", max_length=20)
    department_id: Optional[str] = None
    district: Optional[str] = "Mysuru"
    taluk: Optional[str] = None
    gram_panchayat: Optional[str] = None
    scheme_name: Optional[str] = "MGNREGA"
    audit_type: Optional[str] = "Statutory"
    project_name: Optional[str] = None
    estimated_cost: Optional[Decimal] = None
    actual_expenditure: Optional[Decimal] = None
    sanctioned_amount: Optional[Decimal] = None
    planned_start_date: Optional[date] = None
    due_date: Optional[date] = None
    priority: Optional[str] = "medium"
    lead_auditor_id: Optional[str] = None
    remarks: Optional[str] = None
    scope_notes: Optional[str] = None


class CaseUpdateIn(BaseModel):
    title: Optional[str] = None
    financial_year: Optional[str] = None
    department_id: Optional[str] = None
    district: Optional[str] = None
    taluk: Optional[str] = None
    gram_panchayat: Optional[str] = None
    scheme_name: Optional[str] = None
    audit_type: Optional[str] = None
    project_name: Optional[str] = None
    estimated_cost: Optional[Decimal] = None
    actual_expenditure: Optional[Decimal] = None
    sanctioned_amount: Optional[Decimal] = None
    planned_start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    risk_level: Optional[str] = None
    lead_auditor_id: Optional[str] = None
    remarks: Optional[str] = None
    scope_notes: Optional[str] = None


class CaseStatusTransitionIn(BaseModel):
    to_status: str
    notes: Optional[str] = None


class CaseReopenIn(BaseModel):
    reason: str = Field(..., min_length=10)


class CaseReassignIn(BaseModel):
    lead_auditor_id: str
    notes: Optional[str] = None


class CaseOut(BaseModel):
    id: str
    case_number: str
    title: str
    financial_year: str
    department_id: str
    department_name: Optional[str] = None
    district: Optional[str] = None
    taluk: Optional[str] = None
    gram_panchayat: Optional[str] = None
    scheme_name: Optional[str] = None
    audit_type: str = "Statutory"
    project_name: Optional[str] = None
    estimated_cost: Optional[float] = None
    actual_expenditure: Optional[float] = None
    sanctioned_amount: Optional[float] = None
    planned_start_date: Optional[date] = None
    due_date: Optional[date] = None
    version: int = 1
    priority: str = "medium"
    status: str = "draft"
    risk_level: str = "low"
    is_locked: bool = False
    lead_auditor_id: Optional[str] = None
    lead_auditor_name: Optional[str] = None
    remarks: Optional[str] = None
    scope_notes: Optional[str] = None
    document_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


def _to_case_out(c: AuditCase, db: Session) -> CaseOut:
    doc_count = db.query(Document).filter(Document.case_id == c.id, Document.deleted_at.is_(None)).count()
    status_lower = (c.status or "draft").lower()
    is_locked = status_lower in ["approved", "closed"]
    return CaseOut(
        id=c.id,
        case_number=c.case_number,
        title=c.title,
        financial_year=c.financial_year,
        department_id=c.department_id,
        department_name=c.department.name if c.department else None,
        district=c.district,
        taluk=c.taluk,
        gram_panchayat=c.gram_panchayat,
        scheme_name=c.scheme_name,
        audit_type=c.audit_type or "Statutory",
        project_name=c.project_name,
        estimated_cost=float(c.estimated_cost) if c.estimated_cost is not None else None,
        actual_expenditure=float(c.actual_expenditure) if c.actual_expenditure is not None else None,
        sanctioned_amount=float(c.sanctioned_amount) if c.sanctioned_amount is not None else None,
        planned_start_date=c.planned_start_date,
        due_date=c.due_date,
        version=c.version or 1,
        priority=c.priority or "medium",
        status=c.status,
        risk_level=c.risk_level,
        is_locked=is_locked,
        lead_auditor_id=c.lead_auditor_id,
        lead_auditor_name=c.lead_auditor.full_name if c.lead_auditor else None,
        remarks=c.remarks,
        scope_notes=c.scope_notes,
        document_count=doc_count,
        created_at=c.created_at,
    )


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("", response_model=List[CaseOut])
def list_cases(
    search: Optional[str] = None,
    district: Optional[str] = None,
    scheme: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    financial_year: Optional[str] = None,
    lead_auditor_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists audit cases with optional search and filters."""
    query = db.query(AuditCase).filter(AuditCase.deleted_at.is_(None))

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (AuditCase.case_number.ilike(search_fmt)) |
            (AuditCase.title.ilike(search_fmt)) |
            (AuditCase.project_name.ilike(search_fmt))
        )
    if district:
        query = query.filter(AuditCase.district == district)
    if scheme:
        query = query.filter(AuditCase.scheme_name == scheme)
    if status_filter:
        query = query.filter(AuditCase.status == status_filter)
    if financial_year:
        query = query.filter(AuditCase.financial_year == financial_year)
    if lead_auditor_id:
        query = query.filter(AuditCase.lead_auditor_id == lead_auditor_id)

    cases = query.order_by(AuditCase.created_at.desc()).all()
    return [_to_case_out(c, db) for c in cases]


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Creates a new audit case with auto-generated case ID and audit trail log."""
    year_prefix = payload.financial_year[:4] if len(payload.financial_year) >= 4 else "2024"
    count = db.query(AuditCase).count() + 1
    case_number = f"SAI-{year_prefix}-{count:04d}"

    while db.query(AuditCase).filter(AuditCase.case_number == case_number).first():
        count += 1
        case_number = f"SAI-{year_prefix}-{count:04d}"

    dept_id = payload.department_id
    if not dept_id:
        first_dept = db.query(Department).first()
        dept_id = first_dept.id if first_dept else None

    new_case = AuditCase(
        case_number=case_number,
        title=payload.title,
        financial_year=payload.financial_year,
        department_id=dept_id,
        district=payload.district,
        taluk=payload.taluk,
        gram_panchayat=payload.gram_panchayat,
        scheme_name=payload.scheme_name,
        audit_type=payload.audit_type or "Statutory",
        project_name=payload.project_name,
        estimated_cost=payload.estimated_cost,
        actual_expenditure=payload.actual_expenditure,
        sanctioned_amount=payload.sanctioned_amount,
        planned_start_date=payload.planned_start_date,
        due_date=payload.due_date,
        version=1,
        priority=payload.priority or "medium",
        lead_auditor_id=payload.lead_auditor_id or current_user.id,
        status="draft",
        risk_level="low",
        remarks=payload.remarks,
        scope_notes=payload.scope_notes,
    )
    db.add(new_case)
    db.flush()

    history = CaseStatusHistory(
        case_id=new_case.id,
        from_status=None,
        to_status="draft",
        changed_by=current_user.id,
        notes="Case initiated in Draft status.",
    )
    db.add(history)
    db.commit()
    db.refresh(new_case)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CASE_CREATED",
        entity_type="audit_case",
        entity_id=new_case.id,
        case_id=new_case.id,
        payload={
            "case_number": new_case.case_number,
            "title": new_case.title,
            "district": new_case.district,
            "scheme": new_case.scheme_name,
        },
    )

    return _to_case_out(new_case, db)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves single audit case details."""
    c = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Audit case not found")
    return _to_case_out(c, db)


@router.put("/{case_id}", response_model=CaseOut)
@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: str,
    payload: CaseUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor"])),
):
    """Updates audit case details and records change in audit trail."""
    c = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Audit case not found")

    if c.status and c.status.lower() in ["approved", "closed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Audit case is locked ({c.status.title()}). Edits are prohibited.",
        )

    updates = payload.model_dump(exclude_unset=True)
    old_status = c.status

    for k, v in updates.items():
        setattr(c, k, v)

    if "status" in updates and updates["status"] != old_status:
        history = CaseStatusHistory(
            case_id=c.id,
            from_status=old_status,
            to_status=updates["status"],
            changed_by=current_user.id,
            notes=f"Status transitioned from {old_status} to {updates['status']}",
        )
        db.add(history)

    db.commit()
    db.refresh(c)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CASE_UPDATED",
        entity_type="audit_case",
        entity_id=c.id,
        case_id=c.id,
        payload=str(updates),
    )

    return _to_case_out(c, db)


@router.post("/{case_id}/status", response_model=CaseOut)
def transition_case_status(
    case_id: str,
    payload: CaseStatusTransitionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enforces valid 7-state transitions and prerequisite gates:
    - verification -> review requires at least one completed verification run.
    - review -> approved requires Senior Auditor / Audit Officer AND zero open/escalated/clarification High/Critical findings.
    - approved -> closed requires Audit Officer.
    """
    c = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Audit case not found")

    curr_status = (c.status or "draft").lower()
    next_status = payload.to_status.strip().lower()

    if curr_status in ["approved", "closed"] and next_status != "closed":
        raise HTTPException(
            status_code=400,
            detail=f"Audit case is locked ({c.status.title()}). Use /reopen endpoint to unlock.",
        )

    allowed = VALID_TRANSITIONS.get(curr_status, [])
    if next_status not in allowed and next_status != curr_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from '{c.status}' to '{payload.to_status}'. Allowed: {allowed}",
        )

    user_roles = []
    if current_user.role:
        user_roles = [
            (current_user.role.code or "").lower(),
            (current_user.role.name or "").lower().replace(" ", "_"),
        ]

    # Gate: verification -> review requires verification run
    if curr_status == "verification" and next_status == "review":
        run_count = db.query(RuleRun).filter(RuleRun.case_id == c.id).count()
        if run_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot transition to Review without at least one completed verification run.",
            )

    # Gate: review -> approved requires Senior Auditor or higher & no blocking findings
    if next_status == "approved":
        if not any(r in ["senior_auditor", "audit_officer", "administrator"] for r in user_roles):
            raise HTTPException(
                status_code=403,
                detail="Only Senior Auditor, Audit Officer, or Administrator can approve an audit case.",
            )

        blocking = db.query(Finding).filter(
            Finding.case_id == c.id,
            Finding.deleted_at.is_(None),
            func.lower(Finding.risk_level).in_(["high", "critical"]),
            func.lower(Finding.status).in_(["open", "escalated", "needs_clarification", "pending_approval", "needs clarification", "pending approval"]),
        ).all()

        if blocking:
            blocker_list = [
                {
                    "id": f.id,
                    "finding_number": f.finding_number,
                    "title": f.title,
                    "severity": f.risk_level,
                    "status": f.status,
                }
                for f in blocking
            ]
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Cannot approve case with unresolved High or Critical findings.",
                    "blocking_findings": blocker_list,
                },
            )

    # Gate: to closed requires Audit Officer
    if next_status == "closed":
        if not any(r in ["audit_officer", "administrator"] for r in user_roles):
            raise HTTPException(
                status_code=403,
                detail="Only Audit Officer or Administrator can close an audit case.",
            )

    old_status = c.status
    c.status = next_status
    db.flush()

    history = CaseStatusHistory(
        case_id=c.id,
        from_status=old_status,
        to_status=next_status,
        changed_by=current_user.id,
        notes=payload.notes or f"Transitioned from {old_status} to {next_status}",
    )
    db.add(history)
    db.commit()
    db.refresh(c)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CASE_STATUS_CHANGED",
        entity_type="audit_case",
        entity_id=c.id,
        case_id=c.id,
        payload={"from_status": old_status, "to_status": next_status, "notes": payload.notes},
    )

    return _to_case_out(c, db)


@router.post("/{case_id}/reopen", response_model=CaseOut)
def reopen_case(
    case_id: str,
    payload: CaseReopenIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["audit_officer", "administrator"])),
):
    """
    Reopens an Approved or Closed case. Creates a version snapshot, increments version,
    and transitions status back to 'review'.
    """
    c = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Audit case not found")

    status_lower = (c.status or "").lower()
    if status_lower not in ["approved", "closed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Only Approved or Closed cases can be reopened. Current status: {c.status}",
        )

    doc_count = db.query(Document).filter(Document.case_id == c.id, Document.deleted_at.is_(None)).count()
    finding_count = db.query(Finding).filter(Finding.case_id == c.id, Finding.deleted_at.is_(None)).count()

    snapshot = {
        "case_number": c.case_number,
        "title": c.title,
        "version_prior": c.version or 1,
        "previous_status": c.status,
        "total_documents": doc_count,
        "total_findings": finding_count,
        "reopened_at": datetime.now(timezone.utc).isoformat(),
        "reopened_by": current_user.full_name,
    }

    new_version_num = (c.version or 1) + 1
    c.version = new_version_num

    case_ver = CaseVersion(
        case_id=c.id,
        version_number=new_version_num,
        reopened_by_id=current_user.id,
        reopen_reason=payload.reason,
        snapshot_json=json.dumps(snapshot),
    )
    db.add(case_ver)

    old_status = c.status
    c.status = "review"

    history = CaseStatusHistory(
        case_id=c.id,
        from_status=old_status,
        to_status="review",
        changed_by=current_user.id,
        notes=f"Case reopened (Version {new_version_num}): {payload.reason}",
    )
    db.add(history)
    db.commit()
    db.refresh(c)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CASE_REOPENED",
        entity_type="audit_case",
        entity_id=c.id,
        case_id=c.id,
        payload={"version": new_version_num, "reason": payload.reason},
    )

    return _to_case_out(c, db)


@router.post("/{case_id}/reassign", response_model=CaseOut)
def reassign_case(
    case_id: str,
    payload: CaseReassignIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["senior_auditor", "audit_officer", "administrator"])),
):
    """Reassigns the lead auditor for a case."""
    c = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Audit case not found")

    target_user = db.query(User).filter(User.id == payload.lead_auditor_id, User.deleted_at.is_(None)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target auditor not found")

    old_lead_id = c.lead_auditor_id
    c.lead_auditor_id = payload.lead_auditor_id
    db.commit()
    db.refresh(c)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="CASE_REASSIGNED",
        entity_type="audit_case",
        entity_id=c.id,
        case_id=c.id,
        payload={
            "previous_lead_id": old_lead_id,
            "new_lead_id": target_user.id,
            "new_lead_name": target_user.full_name,
            "notes": payload.notes,
        },
    )

    return _to_case_out(c, db)


@router.get("/{case_id}/detail")
def get_case_detail(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns rich data for the 7 tabs:
    1. Overview, 2. Documents, 3. Extracted Data, 4. Verification, 5. Findings, 6. Reports, 7. Timeline.
    """
    c = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Audit case not found")

    case_out = _to_case_out(c, db)

    # Budget & Financial calculations
    sanctioned = float(c.sanctioned_amount) if c.sanctioned_amount is not None else 0.0
    actual = float(c.actual_expenditure) if c.actual_expenditure is not None else 0.0
    estimated = float(c.estimated_cost) if c.estimated_cost is not None else 0.0
    variance = round(sanctioned - actual, 2)
    budget_utilization = round((actual / sanctioned * 100), 1) if sanctioned > 0 else 0.0

    # Documents summary
    docs = db.query(Document).filter(Document.case_id == c.id, Document.deleted_at.is_(None)).all()
    doc_types: Dict[str, int] = {}
    for d in docs:
        t = d.document_type or "Unknown"
        doc_types[t] = doc_types.get(t, 0) + 1

    # Findings summary
    findings = db.query(Finding).filter(Finding.case_id == c.id, Finding.deleted_at.is_(None)).all()
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    status_counts = {"open": 0, "confirmed": 0, "dismissed": 0, "needs_clarification": 0, "escalated": 0, "pending_approval": 0, "auto_resolved": 0}
    total_flagged_amount = 0.0
    for f in findings:
        sev = (f.risk_level or "low").lower()
        if sev in sev_counts:
            sev_counts[sev] += 1
        st = (f.status or "open").lower().replace(" ", "_")
        if st in status_counts:
            status_counts[st] += 1
        total_flagged_amount += float(f.amount_at_risk) if f.amount_at_risk is not None else 0.0

    # Verification summary
    rule_runs = db.query(RuleRun).filter(RuleRun.case_id == c.id).order_by(RuleRun.created_at.desc()).all()
    last_run = rule_runs[0].created_at if rule_runs else None

    # Status history
    history = db.query(CaseStatusHistory).filter(CaseStatusHistory.case_id == c.id).order_by(CaseStatusHistory.created_at.asc()).all()

    # Case versions
    versions = db.query(CaseVersion).filter(CaseVersion.case_id == c.id).order_by(CaseVersion.version_number.desc()).all()

    return {
        "case": case_out,
        "financial_summary": {
            "sanctioned_amount": sanctioned,
            "estimated_cost": estimated,
            "actual_expenditure": actual,
            "variance": variance,
            "budget_utilization_pct": budget_utilization,
        },
        "documents_summary": {
            "total_documents": len(docs),
            "by_type": doc_types,
        },
        "findings_summary": {
            "total_findings": len(findings),
            "total_flagged_amount": round(total_flagged_amount, 2),
            "severity_counts": sev_counts,
            "status_counts": status_counts,
        },
        "verification_summary": {
            "total_runs": len(rule_runs),
            "last_run_at": last_run,
        },
        "status_history": [
            {
                "id": h.id,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "changed_by": h.user.full_name if h.user else "System",
                "notes": h.notes,
                "created_at": h.created_at,
            }
            for h in history
        ],
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "reopened_by": v.reopened_by.full_name if v.reopened_by else "System",
                "reopen_reason": v.reopen_reason,
                "snapshot": json.loads(v.snapshot_json) if v.snapshot_json else {},
                "created_at": v.created_at,
            }
            for v in versions
        ],
        "is_locked": case_out.is_locked,
    }
