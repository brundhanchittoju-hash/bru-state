from datetime import datetime, timezone
from decimal import Decimal
import json
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.audit_case import AuditCase, CaseStatusHistory
from app.models.audit_trail import ActivityLog
from app.models.finding import Finding
from app.models.rules import RuleRun, VerificationRule
from app.models.system import Holiday, Job
from app.services.audit_trail import log_activity
from app.services.verification.record_linker import link_financial_records_for_case
from app.services.verification.records_layer import build_financial_records_for_case
from app.services.verification.risk_engine import calculate_case_risk_score
from app.services.verification.rules.base import FindingCandidate, VerificationContext
from app.services.verification.rules.registry import get_all_rules, sync_rules_to_db


def generate_next_finding_number(db: Session) -> str:
    """Generates sequential Finding ID: e.g. F-2025-0001."""
    year = datetime.now(timezone.utc).year
    prefix = f"F-{year}-"
    last_finding = db.query(Finding).filter(
        Finding.finding_number.like(f"{prefix}%")
    ).order_by(Finding.finding_number.desc()).first()

    if last_finding and last_finding.finding_number:
        try:
            seq = int(last_finding.finding_number.split("-")[-1]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


def run_case_verification(
    db: Session,
    case_id: str,
    triggered_by_id: str,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Runs complete idempotent financial verification pipeline for an audit case."""
    start_time = time.time()

    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise ValueError(f"AuditCase {case_id} not found.")

    # 1. Update job progress
    job = None
    if job_id:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 5
            db.flush()

    # 2. Sync rule configurations to DB
    sync_rules_to_db(db)

    # 3. Rebuild Normalized Financial Records Layer
    records = build_financial_records_for_case(db, case_id)
    if job:
        job.progress = 15
        db.flush()

    # 4. Rebuild Payment Chain Links
    links = link_financial_records_for_case(db, case_id)
    if job:
        job.progress = 25
        db.flush()

    # 5. Load State Holidays
    holidays = {h.holiday_date for h in db.query(Holiday).filter(Holiday.deleted_at.is_(None)).all()}

    # 6. Load Case Documents & Transactions
    documents = [d for d in case.documents if d.deleted_at is None]
    transactions = [t for t in case.transactions if t.deleted_at is None]

    # 7. Query active Verification Rules and Thresholds
    db_rules = {vr.rule_code: vr for vr in db.query(VerificationRule).filter(VerificationRule.deleted_at.is_(None)).all()}

    rules = get_all_rules()
    candidates: List[FindingCandidate] = []
    thresholds_snapshot = {}
    rules_executed_count = 0

    total_rules = len(rules)
    for idx, rule in enumerate(rules):
        rule_meta = db_rules.get(rule.id)
        if rule_meta and not rule_meta.is_enabled:
            continue

        # Load active thresholds
        active_thresholds = rule.default_thresholds.copy()
        if rule_meta and rule_meta.parameters_json:
            try:
                active_thresholds.update(json.loads(rule_meta.parameters_json))
            except Exception:
                pass

        thresholds_snapshot[rule.id] = active_thresholds

        ctx = VerificationContext(
            db=db,
            case=case,
            records=records,
            links=links,
            documents=documents,
            transactions=transactions,
            holidays=holidays,
            thresholds=active_thresholds
        )

        rule_findings = rule.run(ctx)
        candidates.extend(rule_findings)
        rules_executed_count += 1

        if job:
            progress = 25 + int(((idx + 1) / total_rules) * 60)
            job.progress = min(85, progress)
            db.flush()

    # 8. Idempotent Finding Synchronization
    existing_findings = db.query(Finding).filter(
        Finding.case_id == case_id,
        Finding.deleted_at.is_(None)
    ).all()

    existing_by_fp = {f.fingerprint: f for f in existing_findings if f.fingerprint}
    candidate_fps = set()

    created_count = 0
    updated_count = 0
    unchanged_count = 0
    auto_resolved_count = 0

    for cand in candidates:
        fp = cand.compute_fingerprint(case_id)
        candidate_fps.add(fp)

        rule_db_obj = db_rules.get(cand.rule_id)

        if fp in existing_by_fp:
            f = existing_by_fp[fp]
            # Check review status: Confirmed, Dismissed, Escalated, Under Review
            if f.status in ("Confirmed", "Dismissed", "Escalated", "Under Review"):
                # NEVER overwrite reviewed findings!
                if f.calculation != cand.calculation or f.amount_at_risk != cand.amount_at_risk:
                    f.data_changed_since_review = True
                unchanged_count += 1
            else:
                # Update open finding with fresh calculations & evidence
                f.title = cand.title
                f.description = cand.description
                f.reason = cand.reason
                f.calculation = cand.calculation
                f.amount_at_risk = cand.amount_at_risk
                f.financial_implication = cand.amount_at_risk
                f.risk_level = cand.severity
                f.confidence = cand.confidence
                f.evidence_json = json.dumps(cand.evidence)
                f.inputs_used_json = json.dumps(cand.inputs_used)
                f.thresholds_used_json = json.dumps(cand.thresholds_used)
                updated_count += 1
        else:
            # Create new finding
            f_num = generate_next_finding_number(db)
            new_f = Finding(
                case_id=case_id,
                rule_id=rule_db_obj.id if rule_db_obj else None,
                finding_number=f_num,
                fingerprint=fp,
                category=cand.category,
                title=cand.title,
                description=cand.description,
                reason=cand.reason,
                calculation=cand.calculation,
                risk_level=cand.severity,
                status="Open",
                financial_implication=cand.amount_at_risk,
                amount_at_risk=cand.amount_at_risk,
                confidence=cand.confidence,
                evidence_json=json.dumps(cand.evidence),
                inputs_used_json=json.dumps(cand.inputs_used),
                thresholds_used_json=json.dumps(cand.thresholds_used),
                data_changed_since_review=False,
                assigned_auditor_id=case.lead_auditor_id
            )
            db.add(new_f)
            created_count += 1

    # 9. Auto-Resolve Cleared Findings
    for f in existing_findings:
        if f.fingerprint and f.fingerprint not in candidate_fps:
            if f.status == "Open":
                f.status = "Auto-resolved (condition no longer detected)"
                f.auto_resolved_at = datetime.now(timezone.utc)
                auto_resolved_count += 1

    db.flush()

    # 10. Update Case Risk Score and Status
    all_current_findings = db.query(Finding).filter(
        Finding.case_id == case_id,
        Finding.deleted_at.is_(None)
    ).all()

    total_spend = sum((r.total_amount for r in records if r.record_type in ("voucher", "bank_debit", "bill")), Decimal("0.00"))
    unlinked_count = len([r for r in records if not r.outgoing_links and not r.incoming_links])

    case_score, risk_band, factor_breakdown = calculate_case_risk_score(
        db, case_id, all_current_findings, total_spend, unlinked_count
    )

    case.risk_level = risk_band
    # Case status transition to 'verification' if previously draft or processing
    if case.status in ("draft", "processing"):
        prev_status = case.status
        case.status = "verification"
        status_log = CaseStatusHistory(
            case_id=case.id,
            from_status=prev_status,
            to_status="verification",
            changed_by=triggered_by_id,
            notes="Automatic progression upon financial verification execution."
        )
        db.add(status_log)

    duration_ms = int((time.time() - start_time) * 1000)

    # 11. Record Rule Run History
    summary_data = {
        "rules_executed": rules_executed_count,
        "findings_created": created_count,
        "findings_updated": updated_count,
        "findings_unchanged": unchanged_count,
        "findings_auto_resolved": auto_resolved_count,
        "total_active_findings": len([f for f in all_current_findings if f.status == "Open"]),
        "case_risk_score": case_score,
        "risk_band": risk_band,
        "factor_breakdown": factor_breakdown
    }

    # Pick first rule or dummy rule for the overall run log
    first_rule_id = next(iter(db_rules.values())).id if db_rules else None
    if first_rule_id:
        rule_run = RuleRun(
            case_id=case_id,
            rule_id=first_rule_id,
            triggered_by=triggered_by_id,
            status="completed",
            items_evaluated=len(records),
            findings_count=len(all_current_findings),
            thresholds_snapshot_json=json.dumps(thresholds_snapshot),
            execution_summary_json=json.dumps(summary_data),
            duration_ms=duration_ms
        )
        db.add(rule_run)

    # 12. Write to Cryptographic Audit Trail
    audit_payload = {
        "case_id": case_id,
        "case_number": case.case_number,
        "summary": summary_data,
        "duration_ms": duration_ms
    }
    log_activity(
        db=db,
        action="RUN_VERIFICATION",
        entity_type="AuditCase",
        entity_id=case_id,
        actor_id=triggered_by_id,
        case_id=case_id,
        payload=audit_payload
    )

    # 13. Complete Job
    if job:
        job.status = "completed"
        job.progress = 100
        job.payload_json = json.dumps(summary_data)

    db.commit()

    return summary_data
