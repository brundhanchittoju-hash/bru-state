import csv
import io
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase
from app.models.audit_trail import ActivityLog
from app.models.document import Document, DocumentAnnotation, ExtractedField
from app.models.financial import FinancialRecord, RecordLink, Vendor
from app.models.finding import Finding, FindingClarification, FindingEvidence, FindingNote, FindingReview
from app.models.rules import VerificationRule
from app.models.user import Department, User
from app.services.audit_trail import log_activity
from app.services.extraction.effective_value import get_effective_field_value
from app.services.verification.risk_engine import DEFAULT_RISK_WEIGHTS, get_risk_weights

router = APIRouter(prefix="/findings", tags=["Findings & Evidence"])


@router.get("")
def list_findings(
    financial_year: Optional[str] = None,
    district: Optional[str] = None,
    department_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_auditor_id: Optional[str] = None,
    rule_id: Optional[str] = None,
    category: Optional[str] = None,
    case_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns paginated, multi-filtered findings with summary counters from the database.
    """
    q = db.query(Finding).join(AuditCase, Finding.case_id == AuditCase.id).filter(Finding.deleted_at.is_(None))

    # Apply filters
    if financial_year:
        q = q.filter(AuditCase.financial_year == financial_year)
    if district:
        q = q.filter(AuditCase.district == district)
    if department_id:
        q = q.filter(AuditCase.department_id == department_id)
    if risk_level:
        q = q.filter(func.lower(Finding.risk_level) == risk_level.lower())
    if status_filter:
        q = q.filter(Finding.status == status_filter)
    if assigned_auditor_id:
        q = q.filter(Finding.assigned_auditor_id == assigned_auditor_id)
    if rule_id:
        q = q.filter(Finding.rule_id == rule_id)
    if category:
        q = q.filter(Finding.category == category)
    if case_id:
        q = q.filter(Finding.case_id == case_id)
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            q = q.filter(Finding.created_at >= df)
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            q = q.filter(Finding.created_at <= dt)
        except Exception:
            pass
    if search:
        search_pattern = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Finding.finding_number.ilike(search_pattern),
                Finding.title.ilike(search_pattern),
                Finding.description.ilike(search_pattern),
                AuditCase.case_number.ilike(search_pattern),
                AuditCase.title.ilike(search_pattern)
            )
        )

    # Calculate overall summary metrics across the filtered dataset
    total_count = q.count()

    status_counts_raw = (
        q.with_entities(Finding.status, func.count(Finding.id))
        .group_by(Finding.status)
        .all()
    )
    by_status = {
        "Open": 0,
        "Confirmed": 0,
        "Dismissed": 0,
        "Needs Clarification": 0,
        "Escalated": 0,
        "Pending Approval": 0,
        "Auto-resolved": 0
    }
    for st, cnt in status_counts_raw:
        if st in by_status:
            by_status[st] = cnt
        elif "Auto-resolved" in st:
            by_status["Auto-resolved"] += cnt

    risk_counts_raw = (
        q.with_entities(func.lower(Finding.risk_level), func.count(Finding.id))
        .group_by(func.lower(Finding.risk_level))
        .all()
    )
    by_risk = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for rk, cnt in risk_counts_raw:
        if rk in by_risk:
            by_risk[rk] = cnt

    total_amount = (
        q.with_entities(func.sum(Finding.amount_at_risk))
        .scalar() or Decimal("0.00")
    )

    # Sorting
    sort_column = Finding.created_at
    if sort_by == "finding_number":
        sort_column = Finding.finding_number
    elif sort_by == "amount_at_risk":
        sort_column = Finding.amount_at_risk
    elif sort_by == "risk_level":
        sort_column = Finding.risk_level
    elif sort_by == "status":
        sort_column = Finding.status

    if sort_order.lower() == "asc":
        q = q.order_by(sort_column.asc())
    else:
        q = q.order_by(sort_column.desc())

    # Pagination
    items_raw = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for f in items_raw:
        c = f.case
        dept = c.department if c else None
        items.append({
            "id": f.id,
            "finding_number": f.finding_number,
            "case_id": f.case_id,
            "case_number": c.case_number if c else None,
            "case_title": c.title if c else None,
            "is_case_locked": c.status in ("Approved", "Closed", "approved", "closed") if c else False,
            "category": f.category,
            "rule_id": f.rule_id,
            "rule_code": f.rule.rule_code if f.rule else f.rule_id,
            "title": f.title,
            "risk_level": f.risk_level.lower(),
            "status": f.status,
            "amount_at_risk": float(f.amount_at_risk),
            "financial_implication": float(f.financial_implication),
            "department_name": dept.name if dept else None,
            "district": c.district if c else None,
            "assigned_auditor_id": f.assigned_auditor_id,
            "assigned_auditor_name": f.assigned_auditor.full_name if f.assigned_auditor else None,
            "confidence": f.confidence,
            "data_changed_since_review": f.data_changed_since_review,
            "created_at": f.created_at.isoformat(),
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
        "summary": {
            "by_status": by_status,
            "by_risk": by_risk,
            "total_amount_at_risk": float(total_amount),
        }
    }


@router.get("/pending-approval")
def list_pending_approval_findings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor"]))
):
    """
    Dedicated maker-checker approval queue for Senior Auditors and above.
    """
    findings = (
        db.query(Finding)
        .filter(Finding.status == "Pending Approval", Finding.deleted_at.is_(None))
        .order_by(Finding.amount_at_risk.desc(), Finding.created_at.asc())
        .all()
    )

    out = []
    for f in findings:
        c = f.case
        # Find who submitted for approval
        last_submission = (
            db.query(FindingReview)
            .filter(FindingReview.finding_id == f.id, FindingReview.new_status == "Pending Approval")
            .order_by(FindingReview.created_at.desc())
            .first()
        )
        out.append({
            "id": f.id,
            "finding_number": f.finding_number,
            "case_id": f.case_id,
            "case_number": c.case_number if c else None,
            "title": f.title,
            "risk_level": f.risk_level.lower(),
            "amount_at_risk": float(f.amount_at_risk),
            "rule_id": f.rule_id,
            "submitted_by_id": last_submission.reviewer_id if last_submission else None,
            "submitted_by_name": last_submission.reviewer.full_name if (last_submission and last_submission.reviewer) else "Auditor",
            "submission_comment": last_submission.comments if last_submission else None,
            "submitted_at": last_submission.created_at.isoformat() if last_submission else f.created_at.isoformat(),
            "can_approve": (last_submission.reviewer_id != current_user.id) if last_submission else True,
        })

    return {
        "count": len(out),
        "items": out,
    }


@router.get("/export")
def export_findings_csv(
    financial_year: Optional[str] = None,
    district: Optional[str] = None,
    department_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_auditor_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exports filtered findings to CSV format with cryptographic audit logging.
    """
    q = db.query(Finding).join(AuditCase, Finding.case_id == AuditCase.id).filter(Finding.deleted_at.is_(None))

    if financial_year:
        q = q.filter(AuditCase.financial_year == financial_year)
    if district:
        q = q.filter(AuditCase.district == district)
    if department_id:
        q = q.filter(AuditCase.department_id == department_id)
    if risk_level:
        q = q.filter(func.lower(Finding.risk_level) == risk_level.lower())
    if status_filter:
        q = q.filter(Finding.status == status_filter)
    if assigned_auditor_id:
        q = q.filter(Finding.assigned_auditor_id == assigned_auditor_id)
    if search:
        search_pattern = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Finding.finding_number.ilike(search_pattern),
                Finding.title.ilike(search_pattern),
                AuditCase.case_number.ilike(search_pattern)
            )
        )

    findings = q.order_by(Finding.amount_at_risk.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Finding Number",
        "Case Number",
        "Case Title",
        "Department",
        "District",
        "Rule ID",
        "Category",
        "Title",
        "Risk Level",
        "Status",
        "Amount at Risk (INR)",
        "Financial Implication (INR)",
        "Assigned Auditor",
        "Created Date"
    ])

    for f in findings:
        c = f.case
        dept = c.department if c else None
        writer.writerow([
            f.finding_number,
            c.case_number if c else "",
            c.title if c else "",
            dept.name if dept else "",
            c.district if c else "",
            f.rule_id or "",
            f.category,
            f.title,
            f.risk_level,
            f.status,
            f"{float(f.amount_at_risk):.2f}",
            f"{float(f.financial_implication):.2f}",
            f.assigned_auditor.full_name if f.assigned_auditor else "Unassigned",
            f.created_at.strftime("%Y-%m-%d %H:%M:%S") if f.created_at else ""
        ])

    log_activity(
        db=db,
        action="EXPORT_FINDINGS_CSV",
        entity_type="Finding",
        entity_id="bulk_export",
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={"exported_rows": len(findings), "user_role": current_user.role.name if current_user.role else "Auditor"}
    )
    db.commit()

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=karnataka_findings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


@router.get("/{finding_id}")
def get_finding_evidence_detail(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns complete explainability payload for the split-pane Evidence Page.
    """
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found.")

    case = f.case
    is_locked = case.status in ("Approved", "Closed", "approved", "closed") if case else False

    # Parse JSON fields
    evidence_list = []
    if f.evidence_json:
        try:
            evidence_list = json.loads(f.evidence_json)
        except Exception:
            evidence_list = []

    inputs_used = {}
    if f.inputs_used_json:
        try:
            inputs_used = json.loads(f.inputs_used_json)
        except Exception:
            inputs_used = {}

    thresholds_used = {}
    if f.thresholds_used_json:
        try:
            thresholds_used = json.loads(f.thresholds_used_json)
        except Exception:
            thresholds_used = {}

    # Documents Used: lookup documents referenced in evidence
    referenced_doc_ids = set()
    for ev in evidence_list:
        doc_id = ev.get("document_id") or ev.get("doc_id")
        if doc_id:
            referenced_doc_ids.add(doc_id)

    docs_used_objs = db.query(Document).filter(Document.id.in_(list(referenced_doc_ids))).all() if referenced_doc_ids else []
    documents_used = []
    for d in docs_used_objs:
        documents_used.append({
            "id": d.id,
            "title": d.title,
            "original_filename": d.original_filename,
            "document_type": d.document_type,
            "current_version": d.current_version,
            "page_count": d.page_count,
            "file_size": d.file_size,
        })

    # Extracted Values used
    extracted_fields_data = []
    if referenced_doc_ids:
        raw_fields = db.query(ExtractedField).filter(ExtractedField.document_id.in_(list(referenced_doc_ids))).all()
        for ef in raw_fields:
            eff_val = get_effective_field_value(ef)
            is_overridden = bool(ef.is_overridden)
            extracted_fields_data.append({
                "id": ef.id,
                "document_id": ef.document_id,
                "field_name": ef.field_name,
                "original_value": ef.extracted_value,
                "effective_value": eff_val,
                "is_overridden": is_overridden,
                "confidence": ef.confidence,
                "extractor": ef.extractor,
                "source_page": ef.source_page,
                "bbox": ef.bbox,
            })

    # Structured Comparison table
    comparison_table = []
    bill_amt = inputs_used.get("bill_amount") or inputs_used.get("invoice_amount")
    voucher_amt = inputs_used.get("voucher_amount")
    ledger_amt = inputs_used.get("ledger_amount")
    bank_amt = inputs_used.get("bank_amount")

    if any([bill_amt, voucher_amt, ledger_amt, bank_amt]):
        rows = [
            ("Bill / Invoice", bill_amt),
            ("Voucher Disbursement", voucher_amt),
            ("Ledger Entry", ledger_amt),
            ("Bank Debit", bank_amt),
        ]
        base_ref = next((float(v) for _, v in rows if v is not None), 0.0)
        for stage, val in rows:
            if val is not None:
                val_flt = float(val)
                diff = round(val_flt - base_ref, 2)
                pct = round((diff / base_ref * 100.0), 2) if base_ref != 0 else 0.0
                comparison_table.append({
                    "stage": stage,
                    "amount": val_flt,
                    "difference": diff,
                    "percentage_variance": pct,
                    "is_variance": abs(diff) > 0.01
                })

    # Risk factor breakdown
    weights = get_risk_weights(db)
    risk_factors = [
        {"factor": "Missing Mandatory Documents", "weight": weights.get("missing_documents", 25), "contribution": 25 if f.rule_id == "R-008" else 0},
        {"factor": "Reconciliation Variance", "weight": weights.get("amount_difference", 20), "contribution": 20 if f.rule_id in ("R-003", "R-005") else 0},
        {"factor": "Duplicate Payments", "weight": weights.get("duplicate_payments", 15), "contribution": 15 if f.rule_id in ("R-001", "R-002") else 0},
        {"factor": "Split Purchases (< ₹5L)", "weight": weights.get("split_purchases", 10), "contribution": 10 if f.rule_id == "R-014" else 0},
        {"factor": "Unsanctioned Excess", "weight": weights.get("unsanctioned_excess", 10), "contribution": 10 if f.rule_id == "R-004" else 0},
        {"factor": "Calculation / Tax Errors", "weight": weights.get("calculation_mismatch", 10), "contribution": 10 if f.rule_id in ("R-006", "R-007") else 0},
        {"factor": "Vendor Concentration", "weight": weights.get("vendor_concentration", 10), "contribution": 10 if f.rule_id == "R-011" else 0},
    ]

    # Reviewer Notes
    notes = (
        db.query(FindingNote)
        .filter(FindingNote.finding_id == f.id, FindingNote.deleted_at.is_(None))
        .order_by(FindingNote.created_at.asc())
        .all()
    )
    notes_data = [
        {
            "id": n.id,
            "author_id": n.author_id,
            "author_name": n.author.full_name if n.author else "Auditor",
            "author_role": n.author.role.name if (n.author and n.author.role) else "Auditor",
            "parent_id": n.parent_id,
            "content": n.content,
            "edited_at": n.edited_at.isoformat() if n.edited_at else None,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]

    # Clarifications
    clarifications = (
        db.query(FindingClarification)
        .filter(FindingClarification.finding_id == f.id, FindingClarification.deleted_at.is_(None))
        .order_by(FindingClarification.created_at.asc())
        .all()
    )
    clarifications_data = [
        {
            "id": cl.id,
            "requested_by_name": cl.requester.full_name if cl.requester else "Auditor",
            "question": cl.question,
            "responded_by_name": cl.responder.full_name if cl.responder else None,
            "response": cl.response,
            "status": cl.status,
            "created_at": cl.created_at.isoformat(),
            "responded_at": cl.responded_at.isoformat() if cl.responded_at else None,
        }
        for cl in clarifications
    ]

    # Timeline from ActivityLog + FindingReview
    reviews = db.query(FindingReview).filter(FindingReview.finding_id == f.id).order_by(FindingReview.created_at.asc()).all()
    activity_events = db.query(ActivityLog).filter(ActivityLog.entity_id == f.id).order_by(ActivityLog.sequence_id.asc()).all()

    timeline = []
    # Add creation event
    timeline.append({
        "event_type": "finding_created",
        "title": "Finding Generated by Rule Engine",
        "actor_name": "Verification Engine",
        "timestamp": f.created_at.isoformat(),
        "details": f"Flagged under {f.rule_id or 'Statutory Rule'} with risk score assessment.",
    })
    for rev in reviews:
        timeline.append({
            "event_type": "status_review",
            "title": f"Review Action: {rev.action.replace('_', ' ').title()}",
            "actor_name": rev.reviewer.full_name if rev.reviewer else "Auditor",
            "actor_role": rev.reviewer_role,
            "timestamp": rev.created_at.isoformat(),
            "details": f"Transitioned from {rev.previous_status} to {rev.new_status}. Comment: {rev.comments}",
        })
    for act in activity_events:
        if act.action not in ("REVIEW_FINDING",):
            timeline.append({
                "event_type": act.action.lower(),
                "title": act.action.replace("_", " ").title(),
                "actor_name": act.actor_name,
                "timestamp": act.timestamp.isoformat() if hasattr(act.timestamp, "isoformat") else str(act.timestamp),
                "details": f"Logged audit event (Seq #{act.sequence_id}).",
            })

    timeline.sort(key=lambda x: x["timestamp"])

    # Related Findings
    related = (
        db.query(Finding)
        .filter(
            Finding.case_id == f.case_id,
            Finding.id != f.id,
            or_(Finding.rule_id == f.rule_id, Finding.category == f.category),
            Finding.deleted_at.is_(None)
        )
        .limit(6)
        .all()
    )
    related_findings = [
        {
            "id": r.id,
            "finding_number": r.finding_number,
            "title": r.title,
            "risk_level": r.risk_level.lower(),
            "status": r.status,
            "amount_at_risk": float(r.amount_at_risk),
            "rule_id": r.rule_id,
        }
        for r in related
    ]

    # Attached Document Annotations
    annotations = db.query(DocumentAnnotation).filter(DocumentAnnotation.finding_id == f.id).all()
    annotations_data = [
        {
            "id": an.id,
            "document_id": an.document_id,
            "page": an.page,
            "bbox": an.bbox,
            "note": an.note,
            "author": an.creator.full_name if an.creator else "Auditor",
            "created_at": an.created_at.isoformat(),
        }
        for an in annotations
    ]

    return {
        "id": f.id,
        "finding_number": f.finding_number,
        "case_id": f.case_id,
        "case_number": case.case_number if case else None,
        "case_title": case.title if case else None,
        "department_name": case.department.name if (case and case.department) else None,
        "district": case.district if case else None,
        "is_case_locked": is_locked,
        "rule_id": f.rule_id,
        "rule_code": f.rule.rule_code if f.rule else f.rule_id,
        "rule_name": f.rule.name if f.rule else f.rule_id,
        "rule_description": f.rule.description if f.rule else None,
        "category": f.category,
        "title": f.title,
        "description": f.description,
        "reason": f.reason,
        "calculation": f.calculation,
        "risk_level": f.risk_level.lower(),
        "status": f.status,
        "amount_at_risk": float(f.amount_at_risk),
        "financial_implication": float(f.financial_implication),
        "confidence": f.confidence,
        "data_changed_since_review": f.data_changed_since_review,
        "assigned_auditor_id": f.assigned_auditor_id,
        "assigned_auditor_name": f.assigned_auditor.full_name if f.assigned_auditor else None,
        "auto_resolved_at": f.auto_resolved_at.isoformat() if f.auto_resolved_at else None,
        "created_at": f.created_at.isoformat(),
        "evidence": evidence_list,
        "documents_used": documents_used,
        "extracted_values": extracted_fields_data,
        "comparison_data": comparison_table,
        "risk_factors": risk_factors,
        "ai_summary": f"Automated analysis flagged potential non-compliance under {f.rule_id or 'statutory rules'}. Recommended for review. Final determination rests with the auditor.",
        "ai_summary_badge": "AI summary: template mode",
        "notes": notes_data,
        "clarifications": clarifications_data,
        "timeline": timeline,
        "related_findings": related_findings,
        "annotations": annotations_data,
        "statutory_notice": "Recommended for review. Final determination rests with the auditor."
    }

