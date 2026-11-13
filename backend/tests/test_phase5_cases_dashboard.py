from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_case import AuditCase, CaseStatusHistory, CaseVersion, ScheduledEvent
from app.models.audit_trail import ActivityLog
from app.models.document import Document, ExtractedField
from app.models.financial import FinancialRecord, Vendor, VendorAlias
from app.models.finding import Finding, FindingReview
from app.models.rules import VerificationRule, RuleRun
from app.models.user import Department, Role, User
from app.core.security import get_password_hash


@pytest.fixture
def phase5_env(db_session: Session):
    """Sets up roles, users, department, and a test case for Phase 5."""
    roles = {
        "admin": db_session.query(Role).filter(Role.name == "Administrator").first(),
        "officer": db_session.query(Role).filter(Role.name == "Audit Officer").first(),
        "senior": db_session.query(Role).filter(Role.name == "Senior Auditor").first(),
        "auditor": db_session.query(Role).filter(Role.name == "Auditor").first(),
    }
    for k, v in list(roles.items()):
        if not v:
            name_map = {"admin": "Administrator", "officer": "Audit Officer", "senior": "Senior Auditor", "auditor": "Auditor"}
            code_map = {"admin": "administrator", "officer": "audit_officer", "senior": "senior_auditor", "auditor": "auditor"}
            r = Role(name=name_map[k], code=code_map[k], description=f"{name_map[k]} role")
            db_session.add(r)
            db_session.flush()
            roles[k] = r

    dept = db_session.query(Department).first()
    if not dept:
        dept = Department(name="Rural Development and Panchayat Raj", code="RDPR")
        db_session.add(dept)
        db_session.flush()

    pwd_hash = get_password_hash("Secret123!")
    users = {}
    for role_key, role_obj in roles.items():
        email = f"phase5_{role_key}@example.karnataka.gov.in"
        u = db_session.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                hashed_password=pwd_hash,
                full_name=f"Phase5 {role_obj.name}",
                role_id=role_obj.id,
                department_id=dept.id,
                is_active=True,
            )
            db_session.add(u)
            db_session.flush()
        users[role_key] = u

    # Create test rule
    rule = db_session.query(VerificationRule).filter(VerificationRule.rule_code == "R-001").first()
    if not rule:
        rule = VerificationRule(
            rule_code="R-001",
            name="Duplicate Payment Voucher Check",
            scheme="MGNREGA",
            severity="high",
            description="Identifies identical payments across vouchers.",
        )
        db_session.add(rule)
        db_session.flush()

    # Create a Vendor
    vendor = db_session.query(Vendor).filter(Vendor.legal_name == "DEMO Cauvery Construction Ltd").first()
    if not vendor:
        vendor = Vendor(
            legal_name="DEMO Cauvery Construction Ltd",
            pan="AAACC1234K",
            gstn="29AAACC1234K1Z5",
            bank_account_no="1234567890",
            bank_ifsc="SBIN0001234",
            is_flagged=True,
        )
        db_session.add(vendor)
        db_session.flush()

    # Create an Audit Case
    case = AuditCase(
        case_number=f"SAI-2024-99{int(datetime.now().timestamp()) % 1000:03d}",
        title="DEMO MGNREGA Taluk Audit 2024-25",
        financial_year="2024-25",
        department_id=dept.id,
        district="Mysuru",
        taluk="Nanjangud",
        gram_panchayat="Hullahalli",
        scheme_name="MGNREGA",
        audit_type="Statutory",
        sanctioned_amount=Decimal("1500000.00"),
        actual_expenditure=Decimal("1420000.00"),
        estimated_cost=Decimal("1500000.00"),
        planned_start_date=date(2024, 4, 1),
        due_date=date(2025, 3, 31),
        status="draft",
        priority="high",
        lead_auditor_id=users["auditor"].id,
    )
    db_session.add(case)
    db_session.commit()

    return {
        "users": users,
        "department": dept,
        "vendor": vendor,
        "rule": rule,
        "case": case,
    }


def _login(client: TestClient, email: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": "Secret123!"})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_case_lifecycle_and_transition_gates(client: TestClient, phase5_env, db_session: Session):
    """
    Tests 7-state transitions:
    - Draft -> Documents Uploaded -> Processing -> Verification
    - Verification -> Review gated on verification run completed
    - Review -> Approved gated on role and zero High/Critical unresolved findings
    - Approved -> Closed gated on Audit Officer
    - Invalid transitions rejected
    """
    case = phase5_env["case"]
    auditor_tok = _login(client, phase5_env["users"]["auditor"].email)
    senior_tok = _login(client, phase5_env["users"]["senior"].email)
    officer_tok = _login(client, phase5_env["users"]["officer"].email)

    headers_auditor = {"Authorization": f"Bearer {auditor_tok}"}
    headers_senior = {"Authorization": f"Bearer {senior_tok}"}
    headers_officer = {"Authorization": f"Bearer {officer_tok}"}

    # 1. Invalid transition from draft to approved
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "approved"}, headers=headers_senior)
    assert res.status_code == 400
    assert "Invalid transition" in res.json()["detail"]

    # 2. Draft -> documents_uploaded -> processing -> verification
    for next_st in ["documents_uploaded", "processing", "verification"]:
        res = client.post(f"/api/cases/{case.id}/status", json={"to_status": next_st}, headers=headers_auditor)
        assert res.status_code == 200, res.text
        assert res.json()["status"] == next_st

    # 3. Verification -> review BLOCKED because 0 verification runs exist
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "review"}, headers=headers_auditor)
    assert res.status_code == 400
    assert "at least one completed verification run" in res.json()["detail"]

    # Add a mock RuleRun
    rr = RuleRun(
        case_id=case.id,
        rule_id=phase5_env["rule"].id,
        triggered_by=phase5_env["users"]["auditor"].id,
        status="completed",
        findings_count=1,
    )
    db_session.add(rr)
    db_session.commit()

    # Now verification -> review SUCCEEDS
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "review"}, headers=headers_auditor)
    assert res.status_code == 200
    assert res.json()["status"] == "review"

    # 4. Review -> approved BLOCKED for regular Auditor (403)
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "approved"}, headers=headers_auditor)
    assert res.status_code == 403

    # Add an unresolved High finding to the case
    finding = Finding(
        case_id=case.id,
        rule_id=phase5_env["rule"].id,
        finding_number="FIND-9901",
        title="Unresolved Duplicate Payment",
        description="Duplicate voucher detected.",
        risk_level="high",
        amount_at_risk=Decimal("45000.00"),
        status="open",
        reason="Duplicate voucher detected.",
    )
    db_session.add(finding)
    db_session.commit()

    # 5. Review -> approved BLOCKED for Senior Auditor because High finding is open
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "approved"}, headers=headers_senior)
    assert res.status_code == 400
    data = res.json()["detail"]
    assert "unresolved High or Critical findings" in data["message"]
    assert len(data["blocking_findings"]) == 1
    assert data["blocking_findings"][0]["finding_number"] == "FIND-9901"

    # Confirm the finding to resolve it
    finding.status = "confirmed"
    db_session.commit()

    # 6. Review -> approved SUCCEEDS for Senior Auditor once High finding is confirmed
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "approved"}, headers=headers_senior)
    assert res.status_code == 200
    assert res.json()["status"] == "approved"
    assert res.json()["is_locked"] is True

    # 7. Approved -> closed SUCCEEDS for Audit Officer
    res = client.post(f"/api/cases/{case.id}/status", json={"to_status": "closed"}, headers=headers_officer)
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_case_lock_and_audit_officer_reopen(client: TestClient, phase5_env, db_session: Session):
    """
    Tests case lock enforcement and reopen workflow:
    - Locked case blocks new documents, overrides, verification runs
    - Reopen blocked for regular auditor
    - Reopen succeeds for Audit Officer, increments version, creates snapshot, restores 'review' status
    """
    case = phase5_env["case"]
    case.status = "approved"
    db_session.commit()

    auditor_tok = _login(client, phase5_env["users"]["auditor"].email)
    officer_tok = _login(client, phase5_env["users"]["officer"].email)
    headers_auditor = {"Authorization": f"Bearer {auditor_tok}"}
    headers_officer = {"Authorization": f"Bearer {officer_tok}"}

    # 1. Document upload blocked on locked case
    file_payload = {"file": ("test.txt", b"sample content", "text/plain")}
    data_payload = {"case_id": case.id, "document_type": "voucher"}
    res = client.post("/api/documents/upload", files=file_payload, data=data_payload, headers=headers_auditor)
    assert res.status_code == 400
    assert "locked" in res.json()["detail"].lower()

    # 2. Verification run blocked on locked case
    res = client.post(f"/api/cases/{case.id}/verify", headers=headers_auditor)
    assert res.status_code == 400
    assert "locked" in res.json()["detail"].lower()

    # 3. Reopen blocked for auditor
    res = client.post(
        f"/api/cases/{case.id}/reopen",
        json={"reason": "Additional voucher submitted for verification."},
        headers=headers_auditor,
    )
    assert res.status_code == 403

    # 4. Reopen SUCCEEDS for Audit Officer
    res = client.post(
        f"/api/cases/{case.id}/reopen",
        json={"reason": "Additional voucher submitted by department for review."},
        headers=headers_officer,
    )
    assert res.status_code == 200, res.text
    case_data = res.json()
    assert case_data["status"] == "review"
    assert case_data["version"] == 2
    assert case_data["is_locked"] is False

    # Check case version in DB
    ver = db_session.query(CaseVersion).filter(CaseVersion.case_id == case.id, CaseVersion.version_number == 2).first()
    assert ver is not None
    assert "Additional voucher" in ver.reopen_reason
    snap = json.loads(ver.snapshot_json)
    assert snap["previous_status"] == "approved"


def test_dashboard_stats_api_vs_db_direct_match(client: TestClient, phase5_env, db_session: Session):
    """
    Direct verification of all 12 KPIs returned by GET /dashboard/stats against raw DB SQL queries.
    """
    admin_tok = _login(client, phase5_env["users"]["admin"].email)
    headers = {"Authorization": f"Bearer {admin_tok}"}

    res = client.get("/api/dashboard/stats", headers=headers)
    assert res.status_code == 200, res.text
    api_kpis = res.json()

    # Direct DB Queries
    db_total_cases = db_session.query(AuditCase).filter(AuditCase.deleted_at.is_(None)).count()
    db_open_cases = db_session.query(AuditCase).filter(
        AuditCase.deleted_at.is_(None),
        ~func.lower(AuditCase.status).in_(["approved", "closed"]),
    ).count()
    db_completed_cases = db_session.query(AuditCase).filter(
        AuditCase.deleted_at.is_(None),
        func.lower(AuditCase.status).in_(["approved", "closed"]),
    ).count()

    db_docs_uploaded = db_session.query(Document).filter(Document.deleted_at.is_(None)).count()
    db_docs_processed = db_session.query(Document).filter(
        Document.deleted_at.is_(None),
        func.lower(Document.status) == "processed",
    ).count()

    db_pending_findings = db_session.query(Finding).filter(
        Finding.deleted_at.is_(None),
        func.lower(Finding.status).in_(["open", "escalated", "needs_clarification", "pending_approval"]),
    ).count()

    db_high_findings = db_session.query(Finding).filter(
        Finding.deleted_at.is_(None),
        func.lower(Finding.risk_level) == "high",
    ).count()
    db_med_findings = db_session.query(Finding).filter(
        Finding.deleted_at.is_(None),
        func.lower(Finding.risk_level) == "medium",
    ).count()
    db_low_findings = db_session.query(Finding).filter(
        Finding.deleted_at.is_(None),
        func.lower(Finding.risk_level) == "low",
    ).count()
    db_crit_findings = db_session.query(Finding).filter(
        Finding.deleted_at.is_(None),
        func.lower(Finding.risk_level) == "critical",
    ).count()

    db_r001 = (
        db_session.query(Finding)
        .join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(Finding.deleted_at.is_(None), VerificationRule.rule_code == "R-001")
        .count()
    )
    db_r003 = (
        db_session.query(Finding)
        .join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(Finding.deleted_at.is_(None), VerificationRule.rule_code == "R-003")
        .count()
    )
    db_r008 = (
        db_session.query(Finding)
        .join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(Finding.deleted_at.is_(None), VerificationRule.rule_code == "R-008")
        .count()
    )

    # Assert 100% exact match between API and raw DB
    assert api_kpis["total_cases"] == db_total_cases
    assert api_kpis["open_cases"] == db_open_cases
    assert api_kpis["completed_cases"] == db_completed_cases
    assert api_kpis["documents_uploaded"] == db_docs_uploaded
    assert api_kpis["documents_processed"] == db_docs_processed
    assert api_kpis["pending_findings"] == db_pending_findings
    assert api_kpis["high_risk_findings"] == db_high_findings
    assert api_kpis["medium_risk_findings"] == db_med_findings
    assert api_kpis["low_risk_findings"] == db_low_findings
    assert api_kpis["critical_risk_findings"] == db_crit_findings
    assert api_kpis["r001_duplicate_payments"] == db_r001
    assert api_kpis["r003_amount_mismatches"] == db_r003
    assert api_kpis["r008_missing_documents"] == db_r008


def test_calendar_crud_and_priority_queue(client: TestClient, phase5_env, db_session: Session):
    """Tests scheduled events CRUD and priority review queue endpoint."""
    senior_tok = _login(client, phase5_env["users"]["senior"].email)
    headers = {"Authorization": f"Bearer {senior_tok}"}

    # Priority queue
    pq_res = client.get("/api/dashboard/priority-queue", headers=headers)
    assert pq_res.status_code == 200
    assert isinstance(pq_res.json(), list)

    # Calendar Event Creation
    event_data = {
        "title": "Statutory Hearing on Taluk MGNREGA Audit",
        "event_date": str(date.today() + timedelta(days=7)),
        "case_id": phase5_env["case"].id,
        "description": "Formal hearing with Gram Panchayat officials",
        "event_type": "hearing",
    }
    create_res = client.post("/api/dashboard/calendar", json=event_data, headers=headers)
    assert create_res.status_code == 201, create_res.text
    ev = create_res.json()
    assert ev["title"] == event_data["title"]
    assert ev["case_number"] == phase5_env["case"].case_number

    # Calendar List
    list_res = client.get("/api/dashboard/calendar", headers=headers)
    assert list_res.status_code == 200
    events = list_res.json()
    assert any(e["id"] == ev["id"] for e in events)

    # Calendar Delete
    del_res = client.delete(f"/api/dashboard/calendar/{ev['id']}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Calendar event removed successfully"


def test_analytics_aggregations(client: TestClient, phase5_env):
    """Tests /analytics/aggregations endpoint returning all 8 visual chart dimensions."""
    admin_tok = _login(client, phase5_env["users"]["admin"].email)
    headers = {"Authorization": f"Bearer {admin_tok}"}

    res = client.get("/api/analytics/aggregations", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert "department_breakdown" in data
    assert "risk_distribution" in data
    assert "monthly_findings_trend" in data
    assert "document_types_processed" in data
    assert "case_completion_rate" in data
    assert "top_rules_triggered" in data
    assert "missing_documents_analysis" in data
    assert "vendor_analysis" in data

    # Validate non-empty structure of standard dimensions
    assert len(data["department_breakdown"]) > 0
    assert len(data["risk_distribution"]) == 5  # 5 demo schemes
    assert len(data["case_completion_rate"]) == 5  # 5 demo districts
    assert len(data["monthly_findings_trend"]) == 12  # 12 months


def test_global_search(client: TestClient, phase5_env):
    """Tests global search across entities with basic search mode badge."""
    auditor_tok = _login(client, phase5_env["users"]["auditor"].email)
    headers = {"Authorization": f"Bearer {auditor_tok}"}

    res = client.get("/api/search?q=MGNREGA", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["basic_search_mode"] is True
    assert "cases" in data["results"]
    assert data["total_results"] >= 1


def test_vendor_dossier_and_validity(client: TestClient, phase5_env):
    """Tests /vendors and /vendors/{id} dossier with PAN/GSTIN validity."""
    admin_tok = _login(client, phase5_env["users"]["admin"].email)
    headers = {"Authorization": f"Bearer {admin_tok}"}

    v = phase5_env["vendor"]
    list_res = client.get("/api/vendors", headers=headers)
    assert list_res.status_code == 200
    vendors = list_res.json()
    assert any(item["id"] == v.id for item in vendors)

    dossier_res = client.get(f"/api/vendors/{v.id}", headers=headers)
    assert dossier_res.status_code == 200
    dossier = dossier_res.json()
    assert dossier["canonical_name"] == v.legal_name
    assert dossier["is_pan_valid"] is True
    assert dossier["is_gstin_valid"] is True
