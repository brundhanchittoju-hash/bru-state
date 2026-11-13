from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase
from app.models.finding import Finding, FindingClarification, FindingReview
from app.models.user import User
from app.services.audit_trail import log_activity

router = APIRouter(prefix="/findings", tags=["Finding Reviews & Workflow"])

# Configurable minimum comment length
MIN_COMMENT_LENGTH = 5


class ReviewActionIn(BaseModel):
    action: str = Field(..., description="confirm, dismiss, needs_clarification, escalate, approve, reject")
    comment: str = Field(..., min_length=MIN_COMMENT_LENGTH, description="Mandatory review justification")
    target_status: Optional[str] = None  # Optional override for approval target


class ReopenIn(BaseModel):
    reason: str = Field(..., min_length=MIN_COMMENT_LENGTH, description="Mandatory reason for reopening finding")


class ClarificationResponseIn(BaseModel):
    response: str = Field(..., min_length=MIN_COMMENT_LENGTH, description="Response to the clarification request")


class BulkAssignIn(BaseModel):
    finding_ids: List[str]
    assigned_auditor_id: str


class BulkClarificationIn(BaseModel):
    finding_ids: List[str]
    comment: str = Field(..., min_length=MIN_COMMENT_LENGTH)


def verify_case_unlocked(db: Session, case_id: str) -> AuditCase:
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Associated audit case not found.")
    if case.status in ("Approved", "Closed", "approved", "closed"):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Audit Case {case.case_number} is {case.status} and locked. Finding modifications are strictly prohibited."
        )
    return case


@router.post("/{finding_id}/review")
def review_finding(
    finding_id: str,
    payload: ReviewActionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    """
    Executes finding state transition with dual-custody maker-checker enforcement.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    old_status = finding.status
    action = payload.action.lower().strip()
    user_role_code = current_user.role.code.lower() if current_user.role else "auditor"
    is_senior_or_above = user_role_code in ("administrator", "audit_officer", "senior_auditor")
    is_high_or_critical = finding.risk_level.lower() in ("high", "critical")

    new_status = old_status

    if action == "confirm":
        if old_status not in ("Open", "Needs Clarification", "Escalated"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: Cannot confirm a finding currently in '{old_status}' status."
            )
        # Maker-checker rule: Auditor on High/Critical moves to Pending Approval
        if not is_senior_or_above and is_high_or_critical:
            new_status = "Pending Approval"
        else:
            new_status = "Confirmed"

    elif action == "dismiss":
        if old_status not in ("Open", "Needs Clarification", "Escalated"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: Cannot dismiss a finding currently in '{old_status}' status."
            )
        # Maker-checker rule: Auditor on High/Critical moves to Pending Approval
        if not is_senior_or_above and is_high_or_critical:
            new_status = "Pending Approval"
        else:
            new_status = "Dismissed"

    elif action == "needs_clarification":
        if old_status not in ("Open", "Escalated", "Pending Approval"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: Cannot request clarification for finding in '{old_status}' status."
            )
        new_status = "Needs Clarification"
        # Record clarification request
        clarification = FindingClarification(
            finding_id=finding.id,
            requested_by_id=current_user.id,
            question=payload.comment,
            status="pending"
        )
        db.add(clarification)

    elif action == "escalate":
        if old_status not in ("Open", "Needs Clarification"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: Cannot escalate a finding in '{old_status}' status."
            )
        new_status = "Escalated"

    elif action == "approve":
        if old_status != "Pending Approval":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: Cannot approve finding not in 'Pending Approval' (current: '{old_status}')."
            )
        if not is_senior_or_above:
            raise HTTPException(
                status_code=403,
                detail="Maker-checker violation: Senior Auditor or Audit Officer role required to approve."
            )

        # Check maker-checker self-approval block
        last_submission = (
            db.query(FindingReview)
            .filter(FindingReview.finding_id == finding.id, FindingReview.new_status == "Pending Approval")
            .order_by(FindingReview.created_at.desc())
            .first()
        )
        if last_submission and last_submission.reviewer_id == current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Maker-checker violation: You cannot approve your own finding review action. Dual-custody sign-off required."
            )

        # Determine target approved status
        if payload.target_status in ("Confirmed", "Dismissed"):
            new_status = payload.target_status
        elif last_submission and last_submission.action == "dismiss":
            new_status = "Dismissed"
        else:
            new_status = "Confirmed"

    elif action == "reject":
        if old_status != "Pending Approval":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: Cannot reject finding not in 'Pending Approval' (current: '{old_status}')."
            )
        if not is_senior_or_above:
            raise HTTPException(
                status_code=403,
                detail="Senior Auditor or Audit Officer role required to reject pending approval."
            )

        last_submission = (
            db.query(FindingReview)
            .filter(FindingReview.finding_id == finding.id, FindingReview.new_status == "Pending Approval")
            .order_by(FindingReview.created_at.desc())
            .first()
        )
        if last_submission and last_submission.reviewer_id == current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Maker-checker violation: You cannot review your own pending finding."
            )

        new_status = "Open"

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unrecognized review action '{action}'. Valid: confirm, dismiss, needs_clarification, escalate, approve, reject."
        )

    # Apply status change
    finding.status = new_status
    finding.data_changed_since_review = False

    # Record review history
    review_record = FindingReview(
        finding_id=finding.id,
        reviewer_id=current_user.id,
        reviewer_role=current_user.role.name if current_user.role else "Auditor",
        action=action,
        comments=payload.comment,
        previous_status=old_status,
        new_status=new_status,
    )
    db.add(review_record)

    # Append to cryptographic audit trail
    log_activity(
        db=db,
        action="REVIEW_FINDING",
        entity_type="Finding",
        entity_id=finding.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=finding.case_id,
        payload={
            "finding_number": finding.finding_number,
            "action": action,
            "previous_status": old_status,
            "new_status": new_status,
            "comment": payload.comment,
            "risk_level": finding.risk_level,
        }
    )

    db.commit()
    db.refresh(finding)

    return {
        "message": f"Finding successfully transitioned from {old_status} to {new_status}.",
        "finding_id": finding.id,
        "previous_status": old_status,
        "status": new_status,
        "action": action,
    }


@router.post("/{finding_id}/clarify-response")
def respond_clarification(
    finding_id: str,
    payload: ClarificationResponseIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    """
    Submits a response to an outstanding clarification request and returns finding to Open status.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    pending_clarification = (
        db.query(FindingClarification)
        .filter(FindingClarification.finding_id == finding.id, FindingClarification.status == "pending")
        .order_by(FindingClarification.created_at.desc())
        .first()
    )

    if not pending_clarification:
        # Create an answered clarification entry
        pending_clarification = FindingClarification(
            finding_id=finding.id,
            requested_by_id=current_user.id,
            question="Clarification requested by audit team",
            status="pending"
        )
        db.add(pending_clarification)

    pending_clarification.response = payload.response
    pending_clarification.responded_by_id = current_user.id
    pending_clarification.responded_at = datetime.now(timezone.utc)
    pending_clarification.status = "answered"

    old_status = finding.status
    finding.status = "Open"

    review_record = FindingReview(
        finding_id=finding.id,
        reviewer_id=current_user.id,
        reviewer_role=current_user.role.name if current_user.role else "Auditor",
        action="clarification_responded",
        comments=payload.response,
        previous_status=old_status,
        new_status="Open",
    )
    db.add(review_record)

    log_activity(
        db=db,
        action="RESPOND_FINDING_CLARIFICATION",
        entity_type="Finding",
        entity_id=finding.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=finding.case_id,
        payload={
            "finding_number": finding.finding_number,
            "response": payload.response,
            "new_status": "Open",
        }
    )

    db.commit()
    return {"message": "Clarification submitted. Finding returned to Open status.", "status": "Open"}


@router.post("/{finding_id}/reopen")
def reopen_finding(
    finding_id: str,
    payload: ReopenIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor"]))
):
    """
    Senior Auditor or Audit Officer reopens a Confirmed or Dismissed finding with documented reason.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    if finding.status not in ("Confirmed", "Dismissed"):
        raise HTTPException(
            status_code=400,
            detail=f"Only 'Confirmed' or 'Dismissed' findings can be reopened (current: '{finding.status}')."
        )

    old_status = finding.status
    finding.status = "Open"

    review_record = FindingReview(
        finding_id=finding.id,
        reviewer_id=current_user.id,
        reviewer_role=current_user.role.name if current_user.role else "Senior Auditor",
        action="reopen",
        comments=payload.reason,
        previous_status=old_status,
        new_status="Open",
    )
    db.add(review_record)

    log_activity(
        db=db,
        action="REOPEN_FINDING",
        entity_type="Finding",
        entity_id=finding.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=finding.case_id,
        payload={
            "finding_number": finding.finding_number,
            "reason": payload.reason,
            "previous_status": old_status,
            "new_status": "Open",
        }
    )

    db.commit()
    return {"message": f"Finding reopened from {old_status} to Open.", "status": "Open"}


@router.post("/bulk/assign")
def bulk_assign_findings(
    payload: BulkAssignIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor"]))
):
    """
    Assigns a list of findings to an auditor (Senior Auditor and above).
    """
    target_user = db.query(User).filter(User.id == payload.assigned_auditor_id, User.is_active == True).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target auditor user not found.")

    findings = db.query(Finding).filter(Finding.id.in_(payload.finding_ids), Finding.deleted_at.is_(None)).all()
    if not findings:
        raise HTTPException(status_code=404, detail="No valid findings found for bulk assignment.")

    updated_count = 0
    for f in findings:
        verify_case_unlocked(db, f.case_id)
        prev_auditor_id = f.assigned_auditor_id
        f.assigned_auditor_id = target_user.id
        updated_count += 1

        log_activity(
            db=db,
            action="BULK_ASSIGN_FINDING",
            entity_type="Finding",
            entity_id=f.id,
            actor_id=current_user.id,
            actor_name=current_user.full_name,
            case_id=f.case_id,
            payload={
                "finding_number": f.finding_number,
                "previous_auditor_id": prev_auditor_id,
                "assigned_auditor_id": target_user.id,
                "assigned_auditor_name": target_user.full_name,
            }
        )

    db.commit()
    return {"message": f"Successfully assigned {updated_count} findings to {target_user.full_name}.", "count": updated_count}


@router.post("/bulk/clarify")
def bulk_clarify_findings(
    payload: BulkClarificationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    """
    Transitions multiple findings to 'Needs Clarification' with a mandatory comment.
    """
    findings = db.query(Finding).filter(Finding.id.in_(payload.finding_ids), Finding.deleted_at.is_(None)).all()
    if not findings:
        raise HTTPException(status_code=404, detail="No valid findings found.")

    updated_count = 0
    for f in findings:
        verify_case_unlocked(db, f.case_id)
        if f.status in ("Open", "Escalated"):
            old_status = f.status
            f.status = "Needs Clarification"
            clarification = FindingClarification(
                finding_id=f.id,
                requested_by_id=current_user.id,
                question=payload.comment,
                status="pending"
            )
            db.add(clarification)

            review_record = FindingReview(
                finding_id=f.id,
                reviewer_id=current_user.id,
                reviewer_role=current_user.role.name if current_user.role else "Auditor",
                action="bulk_needs_clarification",
                comments=payload.comment,
                previous_status=old_status,
                new_status="Needs Clarification",
            )
            db.add(review_record)

            log_activity(
                db=db,
                action="BULK_CLARIFY_FINDING",
                entity_type="Finding",
                entity_id=f.id,
                actor_id=current_user.id,
                actor_name=current_user.full_name,
                case_id=f.case_id,
                payload={
                    "finding_number": f.finding_number,
                    "previous_status": old_status,
                    "new_status": "Needs Clarification",
                    "comment": payload.comment,
                }
            )
            updated_count += 1

    db.commit()
    return {"message": f"Transitioned {updated_count} findings to Needs Clarification.", "count": updated_count}

