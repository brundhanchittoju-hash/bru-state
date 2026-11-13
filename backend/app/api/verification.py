from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase
from app.models.audit_trail import ActivityLog
from app.models.financial import FinancialRecord, RecordLink, Vendor, VendorAlias
from app.models.finding import Finding
from app.models.rules import RuleRun, RuleSettingsHistory, VerificationRule
from app.models.system import Holiday, Job, MandatoryDocumentChecklist, Setting
from app.models.user import User
from app.services.audit_trail import log_activity
from app.services.verification.risk_engine import (
    DEFAULT_RISK_WEIGHTS,
    calculate_case_risk_score,
    get_risk_weights,
)
from app.services.verification.rules.registry import get_all_rules, get_rule, sync_rules_to_db
from app.services.verification.runner import run_case_verification


router = APIRouter(prefix="", tags=["Verification & Risk Engine"])


# --- Schemas ---

class RuleThresholdUpdateIn(BaseModel):
    is_enabled: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None
    reason: str = Field(..., min_length=3, description="Mandatory reason for changing verification threshold")


class RiskWeightsUpdateIn(BaseModel):
    weights: Dict[str, int]
    reason: str = Field(..., min_length=3, description="Mandatory reason for updating risk factor weights")


class FindingStatusUpdateIn(BaseModel):
    status: str = Field(..., description="Confirmed, Dismissed, Under Review, Escalated")
    comments: str = Field(..., min_length=3)


class MandatoryChecklistIn(BaseModel):
    scheme_name: str
    document_type: str
    is_mandatory: bool = True
    description: Optional[str] = None


class HolidayCreateIn(BaseModel):
    holiday_date: str
    name: str
    state: str = "Karnataka"
    description: Optional[str] = None


# --- Endpoints ---

@router.post("/cases/{case_id}/verify")
def trigger_case_verification(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    """Triggers idempotent financial verification rule engine for the case."""
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Audit case {case_id} not found.")

    if case.status and case.status.lower() in ["approved", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit case is locked ({case.status.title()}). Running verification is prohibited on locked cases.",
        )

    # Create tracked Job
    job = Job(
        job_type="case_verification",
        payload_json=json.dumps({"case_id": case_id, "case_number": case.case_number}),
        status="pending",
        progress=0,
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Execute synchronously for prompt return or immediate background completion
    # In test & local dev, running directly guarantees instant deterministic results
    try:
        summary = run_case_verification(db, case_id=case_id, triggered_by_id=current_user.id, job_id=job.id)
        return {
            "message": "Verification completed successfully.",
            "job_id": job.id,
            "status": "completed",
            "summary": summary
        }
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/cases/{case_id}/verification-summary")
def get_case_verification_summary(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Provides high-level dashboard data: risk score gauge, factor breakdown,

    rule pass/flag/skip status, payment chain reconciliation matrix, and vendor concentration.
    """
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    # Active findings
    findings = db.query(Finding).filter(
        Finding.case_id == case_id,
        Finding.deleted_at.is_(None)
    ).all()

    # Records and links
    records = db.query(FinancialRecord).filter(
        FinancialRecord.case_id == case_id,
        FinancialRecord.deleted_at.is_(None)
    ).all()

    links = db.query(RecordLink).filter(
        RecordLink.case_id == case_id,
        RecordLink.deleted_at.is_(None)
    ).all()

    total_spend = sum((r.total_amount for r in records if r.record_type in ("voucher", "bank_debit", "bill")), Decimal("0.00"))
    unlinked_count = len([r for r in records if not r.outgoing_links and not r.incoming_links])

    score, band, breakdown = calculate_case_risk_score(db, case_id, findings, total_spend, unlinked_count)

    # 1. Rules Grouped Summary
    sync_rules_to_db(db)
    all_rules = get_all_rules()
    findings_by_rule = {}
    for f in findings:
        if f.status in ("Open", "Under Review", "Confirmed", "Escalated"):
            findings_by_rule.setdefault(f.rule_id, []).append(f)

    disbursements = [r for r in records if r.record_type in ("voucher", "bank_debit", "ledger_entry")]

    rules_summary = []
    for r in all_rules:
        f_list = findings_by_rule.get(r.id, [])
        f_count = len(f_list)

        r_status = "pass"
        skip_reason = None

        if f_count > 0:
            r_status = "flagged"
        else:
            # Check skip reasons
            if r.id == "R-013" and len(disbursements) < 8:
                r_status = "skipped"
                skip_reason = f"Insufficient sample size ({len(disbursements)}/8 transactions)"
            elif r.id == "R-015" and len(disbursements) < 50:
                skip_reason = f"Benford test requires N>=50 ({len(disbursements)} present)"

        rules_summary.append({
            "rule_id": r.id,
            "name": r.name,
            "category": r.category,
            "status": r_status,
            "findings_count": f_count,
            "skipped_reason": skip_reason,
            "default_severity": getattr(r, "default_severity", "medium")
        })

    # 2. Reconciliation Matrix (Chain View)
    rec_matrix = []
    bills = [r for r in records if r.record_type == "bill"]
    vouchers = [r for r in records if r.record_type == "voucher"]
    banks = [r for r in records if r.record_type == "bank_debit"]

    link_map = {}
    for l in links:
        link_map.setdefault(l.source_record_id, []).append(l)

    for b in bills:
        # Check links from bill
        v_links = [l for l in link_map.get(b.id, []) if l.link_type == "bill_to_voucher"]
        matched_v = None
        matched_bank = None
        if v_links:
            matched_v = next((v for v in vouchers if v.id == v_links[0].target_record_id), None)
            if matched_v:
                b_links = [l for l in link_map.get(matched_v.id, []) if l.link_type == "voucher_to_bank"]
                if b_links:
                    matched_bank = next((bnk for bnk in banks if bnk.id == b_links[0].target_record_id), None)

        status_flag = "fully_matched" if (matched_v and matched_bank) else "partially_matched" if matched_v else "unmatched"
        rec_matrix.append({
            "bill_id": b.id,
            "bill_number": b.document_number,
            "bill_amount": float(b.total_amount),
            "voucher_id": matched_v.id if matched_v else None,
            "voucher_number": matched_v.document_number if matched_v else None,
            "voucher_amount": float(matched_v.total_amount) if matched_v else None,
            "bank_id": matched_bank.id if matched_bank else None,
            "bank_reference": matched_bank.payment_reference if matched_bank else None,
            "bank_amount": float(matched_bank.total_amount) if matched_bank else None,
            "status": status_flag
        })

    # 3. Vendor Concentration Summary
    vendor_agg = {}
    for d in disbursements:
        if d.vendor_id:
            vendor_agg.setdefault(d.vendor_id, {"amount": Decimal("0.00"), "count": 0})
            vendor_agg[d.vendor_id]["amount"] += d.total_amount
            vendor_agg[d.vendor_id]["count"] += 1

    vendor_summary = []
    for vid, data in sorted(vendor_agg.items(), key=lambda x: x[1]["amount"], reverse=True)[:5]:
        v_obj = db.query(Vendor).filter(Vendor.id == vid).first()
        v_name = v_obj.legal_name if v_obj else f"Vendor {vid[:8]}"
        share_pct = float(round((data["amount"] / total_spend) * Decimal("100.0"), 1)) if total_spend > Decimal("0.00") else 0.0
        vendor_summary.append({
            "vendor_id": vid,
            "vendor_name": v_name,
            "total_spend": float(data["amount"]),
            "payment_count": data["count"],
            "spend_share_pct": share_pct,
            "is_flagged": v_obj.is_flagged if v_obj else False
        })

    # 4. Latest Run details
    latest_run = db.query(RuleRun).filter(RuleRun.case_id == case_id).order_by(RuleRun.run_at.desc()).first()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "risk_score": score,
        "risk_band": band,
        "factor_breakdown": breakdown,
        "total_expenditure": float(total_spend),
        "total_findings": len(findings),
        "active_findings_count": len([f for f in findings if f.status in ("Open", "Under Review", "Confirmed", "Escalated")]),
        "auto_resolved_count": len([f for f in findings if f.status == "Auto-resolved (condition no longer detected)"]),
        "rules_summary": rules_summary,
        "reconciliation_matrix": rec_matrix,
        "vendor_concentration": vendor_summary,
        "last_run_at": latest_run.run_at.isoformat() if latest_run else None,
        "last_run_duration_ms": latest_run.duration_ms if latest_run else 0
    }


@router.get("/cases/{case_id}/findings")
def list_case_findings(
    case_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    rule_id: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns sortable list of findings for a case."""
    q = db.query(Finding).filter(Finding.case_id == case_id, Finding.deleted_at.is_(None))

    if status_filter:
        q = q.filter(Finding.status == status_filter)
    if rule_id:
        q = q.filter(Finding.rule_id == rule_id)
    if severity:
        q = q.filter(Finding.risk_level == severity)
    if category:
        q = q.filter(Finding.category == category)

    findings = q.order_by(Finding.amount_at_risk.desc(), Finding.finding_number.asc()).all()

    results = []
    for f in findings:
        evidence = []
        if f.evidence_json:
            try:
                evidence = json.loads(f.evidence_json)
            except Exception:
                evidence = []

        results.append({
            "id": f.id,
            "finding_number": f.finding_number,
            "rule_id": f.rule_id,
            "category": f.category,
            "title": f.title,
            "description": f.description,
            "reason": f.reason,
            "calculation": f.calculation,
            "risk_level": f.risk_level,
            "status": f.status,
            "financial_implication": float(f.financial_implication),
            "amount_at_risk": float(f.amount_at_risk),
            "confidence": f.confidence,
            "evidence": evidence,
            "data_changed_since_review": f.data_changed_since_review,
            "auto_resolved_at": f.auto_resolved_at.isoformat() if f.auto_resolved_at else None,
            "assigned_auditor_name": f.assigned_auditor.full_name if f.assigned_auditor else None,
            "created_at": f.created_at.isoformat()
        })

    return results


@router.get("/findings/{finding_id}")
def get_finding_detail(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detailed explainability view for a specific finding."""
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found.")

    evidence = []
    inputs_used = {}
    thresholds_used = {}

    if f.evidence_json:
        try:
            evidence = json.loads(f.evidence_json)
        except Exception:
            pass
    if f.inputs_used_json:
        try:
            inputs_used = json.loads(f.inputs_used_json)
        except Exception:
            pass
    if f.thresholds_used_json:
        try:
            thresholds_used = json.loads(f.thresholds_used_json)
        except Exception:
            pass

    return {
        "id": f.id,
        "finding_number": f.finding_number,
        "case_id": f.case_id,
        "rule_id": f.rule_id,
        "category": f.category,
        "title": f.title,
        "description": f.description,
        "reason": f.reason,
        "calculation": f.calculation,
        "risk_level": f.risk_level,
        "status": f.status,
        "amount_at_risk": float(f.amount_at_risk),
        "confidence": f.confidence,
        "evidence": evidence,
        "inputs_used": inputs_used,
        "thresholds_used": thresholds_used,
        "data_changed_since_review": f.data_changed_since_review,
        "auto_resolved_at": f.auto_resolved_at.isoformat() if f.auto_resolved_at else None,
        "created_at": f.created_at.isoformat()
    }


@router.patch("/findings/{finding_id}/status")
def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    """Updates finding review status with mandatory justification and audit trail logging."""
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found.")

    old_status = f.status
    f.status = payload.status
    f.data_changed_since_review = False

    # Log to audit trail
    log_activity(
        db=db,
        action="UPDATE_FINDING_STATUS",
        entity_type="Finding",
        entity_id=f.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=f.case_id,
        payload={
            "finding_id": f.id,
            "finding_number": f.finding_number,
            "old_status": old_status,
            "new_status": payload.status,
            "comments": payload.comments
        }
    )
    db.commit()

    return {"message": f"Finding status updated to {payload.status}.", "status": payload.status}


@router.get("/cases/{case_id}/rule-runs")
def list_case_rule_runs(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns execution run history with threshold snapshots."""
    runs = db.query(RuleRun).filter(RuleRun.case_id == case_id).order_by(RuleRun.run_at.desc()).all()
    out = []
    for r in runs:
        snap = {}
        summ = {}
        if r.thresholds_snapshot_json:
            try:
                snap = json.loads(r.thresholds_snapshot_json)
            except Exception:
                pass
        if r.execution_summary_json:
            try:
                summ = json.loads(r.execution_summary_json)
            except Exception:
                pass

        out.append({
            "id": r.id,
            "run_at": r.run_at.isoformat(),
            "triggered_by_name": r.trigger_user.full_name if r.trigger_user else "System",
            "status": r.status,
            "items_evaluated": r.items_evaluated,
            "findings_count": r.findings_count,
            "duration_ms": r.duration_ms,
            "thresholds_snapshot": snap,
            "summary": summ
        })
    return out


# --- Settings: Verification Rules ---

@router.get("/verification/rules")
def get_verification_rules_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all R-001..R-016 rules with active thresholds and defaults."""
    sync_rules_to_db(db)
    all_rules = get_all_rules()
    db_rules = {vr.rule_code: vr for vr in db.query(VerificationRule).filter(VerificationRule.deleted_at.is_(None)).all()}

    results = []
    for r in all_rules:
        db_r = db_rules.get(r.id)
        params = r.default_thresholds.copy()
        if db_r and db_r.parameters_json:
            try:
                params.update(json.loads(db_r.parameters_json))
            except Exception:
                pass

        results.append({
            "id": db_r.id if db_r else r.id,
            "rule_code": r.id,
            "name": r.name,
            "description": r.description,
            "category": r.category,
            "is_enabled": db_r.is_enabled if db_r else True,
            "parameters": params,
            "default_parameters": r.default_thresholds
        })
    return results


@router.patch("/verification/rules/{rule_code}")
def update_verification_rule_settings(
    rule_code: str,
    payload: RuleThresholdUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    """Administrator only: updates rule thresholds and logs reason to audit trail."""
    rule_code_clean = rule_code.upper()
    rule_obj = get_rule(rule_code_clean)
    if not rule_obj:
        raise HTTPException(status_code=404, detail=f"Rule {rule_code} not found.")

    db_r = db.query(VerificationRule).filter(VerificationRule.rule_code == rule_code_clean).first()
    if not db_r:
        raise HTTPException(status_code=404, detail="Rule configuration not in DB.")

    old_params_str = db_r.parameters_json or "{}"
    if payload.is_enabled is not None:
        db_r.is_enabled = payload.is_enabled
    if payload.parameters is not None:
        db_r.parameters_json = json.dumps(payload.parameters)

    # Record history
    hist = RuleSettingsHistory(
        rule_id=db_r.id,
        old_parameters=old_params_str,
        new_parameters=db_r.parameters_json,
        reason=payload.reason,
        changed_by=current_user.id
    )
    db.add(hist)

    # Audit Trail Entry
    log_activity(
        db=db,
        action="UPDATE_RULE_THRESHOLD",
        entity_type="VerificationRule",
        entity_id=db_r.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={
            "rule_code": rule_code_clean,
            "old_parameters": old_params_str,
            "new_parameters": db_r.parameters_json,
            "is_enabled": db_r.is_enabled,
            "reason": payload.reason
        }
    )
    db.commit()

    return {"message": f"Rule {rule_code_clean} configuration updated.", "parameters": json.loads(db_r.parameters_json)}


@router.post("/verification/rules/{rule_code}/reset")
def reset_verification_rule_defaults(
    rule_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    """Administrator only: resets rule parameters to statutory defaults."""
    rule_code_clean = rule_code.upper()
    rule_obj = get_rule(rule_code_clean)
    if not rule_obj:
        raise HTTPException(status_code=404, detail=f"Rule {rule_code} not found.")

    db_r = db.query(VerificationRule).filter(VerificationRule.rule_code == rule_code_clean).first()
    if not db_r:
        raise HTTPException(status_code=404, detail="Rule record not found.")

    old_params_str = db_r.parameters_json or "{}"
    db_r.parameters_json = json.dumps(rule_obj.default_thresholds)
    db_r.is_enabled = True

    hist = RuleSettingsHistory(
        rule_id=db_r.id,
        old_parameters=old_params_str,
        new_parameters=db_r.parameters_json,
        reason="Reset to statutory default thresholds",
        changed_by=current_user.id
    )
    db.add(hist)
    db.commit()

    return {"message": f"Rule {rule_code_clean} reset to defaults.", "parameters": rule_obj.default_thresholds}


# --- Settings: Risk Weights ---

@router.get("/verification/risk-weights")
def get_risk_weights_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns active risk factor weights."""
    return get_risk_weights(db)


@router.put("/verification/risk-weights")
def update_risk_weights_endpoint(
    payload: RiskWeightsUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    """Administrator only: updates risk weights (strictly validated to sum to 100)."""
    weights = payload.weights
    if sum(weights.values()) != 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Risk factor weights must sum to exactly 100 (current sum: {sum(weights.values())})."
        )

    setting = db.query(Setting).filter(Setting.key == "risk_weights").first()
    old_weights_str = setting.value_json if setting else json.dumps(DEFAULT_RISK_WEIGHTS)

    if not setting:
        setting = Setting(
            key="risk_weights",
            value_json=json.dumps(weights),
            category="verification",
            is_editable=True,
            updated_by=current_user.id
        )
        db.add(setting)
    else:
        setting.value_json = json.dumps(weights)
        setting.updated_by = current_user.id

    # Audit Trail Entry
    log_activity(
        db=db,
        action="UPDATE_RISK_WEIGHTS",
        entity_type="Setting",
        entity_id=setting.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={
            "old_weights": old_weights_str,
            "new_weights": json.dumps(weights),
            "reason": payload.reason
        }
    )
    db.commit()

    return {"message": "Risk factor weights updated successfully.", "weights": weights}


# --- Settings: Mandatory Document Checklists ---

@router.get("/verification/checklists")
def get_mandatory_checklists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all configured mandatory document checklists."""
    return db.query(MandatoryDocumentChecklist).filter(MandatoryDocumentChecklist.deleted_at.is_(None)).all()


@router.post("/verification/checklists")
def create_or_update_mandatory_checklist(
    payload: MandatoryChecklistIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    """Administrator only: adds or updates mandatory document requirements per scheme."""
    item = db.query(MandatoryDocumentChecklist).filter(
        MandatoryDocumentChecklist.scheme_name == payload.scheme_name,
        MandatoryDocumentChecklist.document_type == payload.document_type,
        MandatoryDocumentChecklist.deleted_at.is_(None)
    ).first()

    if not item:
        item = MandatoryDocumentChecklist(
            scheme_name=payload.scheme_name,
            document_type=payload.document_type,
            is_mandatory=payload.is_mandatory,
            description=payload.description
        )
        db.add(item)
    else:
        item.is_mandatory = payload.is_mandatory
        item.description = payload.description

    db.commit()
    db.refresh(item)
    return item


@router.delete("/verification/checklists/{item_id}")
def delete_mandatory_checklist(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    """Administrator only: soft-deletes a mandatory document checklist requirement."""
    item = db.query(MandatoryDocumentChecklist).filter(MandatoryDocumentChecklist.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found.")
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Checklist item removed."}


# --- Settings: Karnataka Holidays ---

@router.get("/verification/holidays")
def list_holidays(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Holiday).filter(Holiday.deleted_at.is_(None)).order_by(Holiday.holiday_date.asc()).all()


@router.post("/verification/holidays")
def create_holiday(
    payload: HolidayCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    from datetime import date
    h_date = date.fromisoformat(payload.holiday_date)
    holiday = Holiday(
        holiday_date=h_date,
        name=payload.name,
        state=payload.state,
        description=payload.description
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.delete("/verification/holidays/{holiday_id}")
def delete_holiday(
    holiday_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator"]))
):
    h = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holiday not found.")
    h.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Holiday deleted."}


# --- Vendor Review UI Endpoints ---

@router.get("/verification/vendor-reviews")
def list_pending_vendor_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists vendor aliases flagged as pending review for human auditor confirmation."""
    aliases = db.query(VendorAlias).filter(
        VendorAlias.status == "pending_review",
        VendorAlias.deleted_at.is_(None)
    ).all()

    out = []
    for a in aliases:
        out.append({
            "alias_id": a.id,
            "suggested_alias_name": a.alias_name,
            "confidence_score": a.confidence_score,
            "primary_vendor_id": a.vendor_id,
            "primary_vendor_name": a.vendor.legal_name if a.vendor else "Unknown"
        })
    return out


@router.post("/verification/vendor-reviews/{alias_id}/confirm")
def confirm_vendor_alias(
    alias_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    alias = db.query(VendorAlias).filter(VendorAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="Vendor alias not found.")
    alias.status = "confirmed"
    db.commit()
    return {"message": f"Vendor alias '{alias.alias_name}' confirmed."}


@router.post("/verification/vendor-reviews/{alias_id}/reject")
def reject_vendor_alias(
    alias_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    alias = db.query(VendorAlias).filter(VendorAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="Vendor alias not found.")
    alias.status = "rejected"
    db.commit()
    return {"message": f"Vendor alias '{alias.alias_name}' rejected."}
