from datetime import datetime, timezone
from decimal import Decimal
import json
import pytest
from sqlalchemy.orm import Session

from app.models.audit_case import AuditCase
from app.models.finding import Finding, FindingNote, FindingReview, FindingClarification
from app.models.rules import VerificationRule
from app.models.system import SavedFilter, UserPreference
from app.models.user import Department, User
from app.services.audit_trail import verify_hash_chain


@pytest.fixture
def test_case(db_session: Session):
    dept = db_session.query(Department).first()
    case = AuditCase(
        case_number="CAS-TEST-PH4-001",
        title="Phase 4 Test Audit Case",
        financial_year="2024-25",
        department_id=dept.id,
        district="Mysuru",
        taluk="Hunsur",
        status="Verification",
        priority="high",
        risk_level="high",
        estimated_cost=Decimal("500000.00"),
        actual_expenditure=Decimal("450000.00"),
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def high_finding(db_session: Session, test_case: AuditCase):
    rule = db_session.query(VerificationRule).filter(VerificationRule.rule_code == "R-001").first()
    f = Finding(
        case_id=test_case.id,
        rule_id=rule.id if rule else None,
        finding_number="F-TEST-HIGH-01",
        category="financial",
        title="Potential duplicate payment detected",
        description="Voucher disbursement matches earlier bill reference.",
        risk_level="high",
        status="Open",
        amount_at_risk=Decimal("125000.00"),
        financial_implication=Decimal("125000.00"),
        confidence=95.0,
        evidence_json=json.dumps([{"document_id": "dummy_doc_1", "page": 1, "excerpt": "Passed ₹1,25,000"}]),
        inputs_used_json=json.dumps({"voucher_amount": 125000.0, "bill_amount": 125000.0}),
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)
    return f


@pytest.fixture
def low_finding(db_session: Session, test_case: AuditCase):
    rule = db_session.query(VerificationRule).filter(VerificationRule.rule_code == "R-016").first()
    f = Finding(
        case_id=test_case.id,
        rule_id=rule.id if rule else None,
        finding_number="F-TEST-LOW-01",
        category="compliance",
        title="Payment processed on non-working day",
        description="Transaction voucher dated on public holiday.",
        risk_level="low",
        status="Open",
        amount_at_risk=Decimal("5000.00"),
        financial_implication=Decimal("5000.00"),
        confidence=80.0,
        evidence_json=json.dumps([]),
        inputs_used_json=json.dumps({"date": "2024-11-01"}),
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)
    return f


# ==============================================================================
# 1. STATE TRANSITION TABLE & MAKER-CHECKER TESTS
# ==============================================================================

def test_auditor_confirms_low_finding_directly(client, auth_tokens, low_finding):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.post(
        f"/api/findings/{low_finding.id}/review",
        json={"action": "confirm", "comment": "Low risk discrepancy verified with sub-treasury records."},
        headers=aud_hdr,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "Confirmed"
    assert res.json()["previous_status"] == "Open"


def test_auditor_confirms_high_finding_triggers_maker_checker(client, auth_tokens, high_finding):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "confirm", "comment": "Duplicate payment evidence confirmed, sending for senior review."},
        headers=aud_hdr,
    )
    assert res.status_code == 200
    # Must transition to Pending Approval
    assert res.json()["status"] == "Pending Approval"
    assert res.json()["previous_status"] == "Open"


def test_maker_checker_self_approval_is_strictly_blocked(client, auth_tokens, high_finding, db_session):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}

    # Auditor submits high finding -> transitions to Pending Approval
    res1 = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "confirm", "comment": "Flagged duplicate disbursement, submitting to senior auditor."},
        headers=aud_hdr,
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "Pending Approval"

    # Auditor attempts to approve own submission -> Blocked
    res_self = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "approve", "comment": "Attempting self-signoff on high finding."},
        headers=aud_hdr,
    )
    assert res_self.status_code == 403

    # Now simulate Senior Auditor having submitted a finding into Pending Approval
    senior_user_id = client.get("/api/auth/me", headers=senior_hdr).json()["id"]
    high_finding.status = "Pending Approval"
    rev = FindingReview(
        finding_id=high_finding.id,
        reviewer_id=senior_user_id,
        reviewer_role="Senior Auditor",
        action="confirm",
        comments="Submitted for approval by Senior Auditor",
        previous_status="Open",
        new_status="Pending Approval"
    )
    db_session.add(rev)
    db_session.commit()

    # Senior Auditor attempts to approve their own submission -> Blocked
    res_sr_self_approve = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "approve", "comment": "Senior Auditor attempting self-approval."},
        headers=senior_hdr,
    )
    assert res_sr_self_approve.status_code == 403
    assert "Maker-checker violation" in res_sr_self_approve.json()["detail"]


def test_senior_auditor_approves_auditor_submission(client, auth_tokens, high_finding):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}

    # Auditor submits
    res_sub = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "confirm", "comment": "Auditor verification complete; requires senior sign-off."},
        headers=aud_hdr,
    )
    assert res_sub.status_code == 200

    # Senior Auditor approves (different user)
    res_appr = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "approve", "comment": "Dual review complete. Duplicate payment evidence sustained."},
        headers=senior_hdr,
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "Confirmed"


def test_comment_required_minimum_length(client, auth_tokens, high_finding):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "confirm", "comment": "ok"},  # Under 5 chars
        headers=aud_hdr,
    )
    assert res.status_code == 422


def test_invalid_transitions_rejected(client, auth_tokens, high_finding):
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}

    # Cannot approve a finding that is currently Open
    res = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "approve", "comment": "Trying to approve directly without pending state."},
        headers=senior_hdr,
    )
    assert res.status_code == 400
    assert "Invalid transition" in res.json()["detail"]


def test_needs_clarification_and_response_flow(client, auth_tokens, high_finding):
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # 1. Senior auditor sets Needs Clarification
    res_cl = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "needs_clarification", "comment": "Please verify if tax deduction was already credited in voucher 12."},
        headers=senior_hdr,
    )
    assert res_cl.status_code == 200
    assert res_cl.json()["status"] == "Needs Clarification"

    # 2. Auditor provides clarification response
    res_resp = client.post(
        f"/api/findings/{high_finding.id}/clarify-response",
        json={"response": "Verified with bank reconciliation; tax was not deducted at source."},
        headers=aud_hdr,
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "Open"


def test_senior_auditor_reopen_flow(client, auth_tokens, high_finding, db_session):
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}

    # Set finding to Confirmed first
    high_finding.status = "Confirmed"
    db_session.commit()

    # Senior Auditor reopens
    res_reopen = client.post(
        f"/api/findings/{high_finding.id}/reopen",
        json={"reason": "New sanction document submitted by Gram Panchayat; reopening for re-evaluation."},
        headers=senior_hdr,
    )
    assert res_reopen.status_code == 200
    assert res_reopen.json()["status"] == "Open"


# ==============================================================================
# 2. CASE LOCK ENFORCEMENT & BULK ACTIONS
# ==============================================================================

def test_case_lock_blocks_finding_modifications(client, auth_tokens, high_finding, test_case, db_session):
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}

    # Lock the case by setting status to Approved
    test_case.status = "Approved"
    db_session.commit()

    res = client.post(
        f"/api/findings/{high_finding.id}/review",
        json={"action": "confirm", "comment": "Attempting modification on locked case."},
        headers=senior_hdr,
    )
    assert res.status_code == 423
    assert "locked" in res.json()["detail"].lower()


def test_bulk_assignment_and_clarification(client, auth_tokens, high_finding, low_finding, db_session):
    senior_hdr = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}
    aud_user = db_session.query(User).filter(User.email == "auditor@stateaudit.kar.gov.in").first()

    # Bulk assign
    res_assign = client.post(
        "/api/findings/bulk/assign",
        json={"finding_ids": [high_finding.id, low_finding.id], "assigned_auditor_id": aud_user.id},
        headers=senior_hdr,
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["count"] == 2

    # Bulk clarify
    res_clarify = client.post(
        "/api/findings/bulk/clarify",
        json={"finding_ids": [high_finding.id, low_finding.id], "comment": "Batch verification: provide supporting bank passbook records."},
        headers=senior_hdr,
    )
    assert res_clarify.status_code == 200
    assert res_clarify.json()["count"] == 2


# ==============================================================================
# 3. CSV EXPORT & AUDIT TRAIL VERIFICATION
# ==============================================================================

def test_csv_export_and_audit_trail_logging(client, auth_tokens, db_session):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.get("/api/findings/export", headers=aud_hdr)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Finding Number" in res.text
    assert "Amount at Risk" in res.text

    # Verify cryptographic hash chain remains intact
    res_chain = verify_hash_chain(db_session)
    assert res_chain["verified"] is True, f"Hash chain broken: {res_chain.get('error')}"


# ==============================================================================
# 4. REVIEWER NOTES CRUD & 24H EDIT WINDOW
# ==============================================================================

def test_reviewer_notes_crud(client, auth_tokens, high_finding):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # 1. Add note
    res_add = client.post(
        f"/api/findings/{high_finding.id}/notes",
        json={"content": "Cross-referenced with KPPP portal tender reference."},
        headers=aud_hdr,
    )
    assert res_add.status_code == 200
    note_id = res_add.json()["note"]["id"]

    # 2. List notes
    res_list = client.get(f"/api/findings/{high_finding.id}/notes", headers=aud_hdr)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Edit note
    res_edit = client.patch(
        f"/api/findings/{high_finding.id}/notes/{note_id}",
        json={"content": "Updated note: Cross-referenced with KPPP portal and confirmed tender award."},
        headers=aud_hdr,
    )
    assert res_edit.status_code == 200

    # 4. Delete note
    res_del = client.delete(f"/api/findings/{high_finding.id}/notes/{note_id}", headers=aud_hdr)
    assert res_del.status_code == 200


# ==============================================================================
# 5. SAVED FILTERS & USER PREFERENCES
# ==============================================================================

def test_saved_filters_and_preferences(client, auth_tokens):
    aud_hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # 1. Save filter
    res_save = client.post(
        "/api/filters/saved",
        json={
            "name": "High Risk Mysuru Findings",
            "entity_type": "findings",
            "filter_json": json.dumps({"district": "Mysuru", "risk_level": "high"})
        },
        headers=aud_hdr,
    )
    assert res_save.status_code == 200
    filter_id = res_save.json()["id"]

    # 2. List saved filters
    res_list = client.get("/api/filters/saved?entity_type=findings", headers=aud_hdr)
    assert res_list.status_code == 200
    assert any(f["id"] == filter_id for f in res_list.json())

    # 3. Update user preference
    res_pref = client.put(
        "/api/users/me/preferences",
        json={"preference_key": "findings_density", "preference_value": "compact"},
        headers=aud_hdr,
    )
    assert res_pref.status_code == 200

    # 4. Get preferences
    res_get_pref = client.get("/api/users/me/preferences", headers=aud_hdr)
    assert res_get_pref.status_code == 200
    assert res_get_pref.json().get("findings_density") == "compact"
