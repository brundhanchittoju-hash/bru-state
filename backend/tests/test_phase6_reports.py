import io
import json
import os
import fitz  # PyMuPDF
import pytest
from app.models.audit_case import AuditCase
from app.models.finding import Finding
from app.models.report import Report, ReportVersion
from app.services.reporting.pdf_generator import AuditReportPDFGenerator


def test_pdf_generator_unit(tmp_path):
    out_pdf = str(tmp_path / "test_report.pdf")
    snapshot = {
        "report_number": "RPT-2025-9999",
        "version_number": 1,
        "case_number": "CAS-2024-TEST-001",
        "report_title": "Statutory Financial Audit Report — Test GP",
        "report_type": "preliminary",
        "financial_year": "2024-25",
        "scheme_name": "MGNREGA",
        "audit_type": "Statutory Compliance",
        "department": "Rural Development & Panchayat Raj",
        "district": "Mysuru",
        "taluk": "Mysuru Taluk",
        "gram_panchayat": "Test Gram Panchayat",
        "lead_auditor_name": "Auditor Test",
        "lead_auditor_role": "Auditor",
        "generated_by_name": "Auditor Test",
        "generated_at_formatted": "30 Oct 2026, 12:00 UTC",
        "status": "Draft",
        "includes_demo_watermark": True,
        "total_expenditure": 1500000.0,
        "total_questioned": 75000.0,
        "findings": [
            {
                "finding_number": "FND-001",
                "rule_id": "R-001",
                "title": "Split procurement below quotation limit",
                "category": "Procurement",
                "risk_score": 85,
                "risk_level": "High",
                "amount": 75000.0,
                "status": "Open",
                "department": "Rural Development",
                "evidence_summary": "Two vouchers issued on same date to avoid tender threshold.",
                "recommended_action": "Recommended for review and physical verification.",
            }
        ],
        "documents": [
            {
                "name": "Cash_Book_2024.pdf",
                "document_type": "Cash Book",
                "file_size": 204850,
                "page_count": 5,
                "created_at": "2024-05-10",
                "status": "Processed",
            }
        ],
        "rules": [
            {
                "rule_code": "R-001",
                "rule_name": "Split Procurement Check",
                "category": "Procurement",
                "status": "FLAGGED",
                "count": 1,
                "severity": "High",
            }
        ],
        "reviewer_notes": [],
        "risk_breakdown": {"Low": 0, "Medium": 0, "High": 1, "Critical": 0},
        "status_breakdown": {"Open": 1},
    }

    gen = AuditReportPDFGenerator(snapshot=snapshot, output_path=out_pdf, public_base_url="http://localhost:5173")
    page_count, sha = gen.build_pdf()

    assert os.path.exists(out_pdf)
    assert page_count >= 1
    assert len(sha) == 64

    # PyMuPDF Inspection
    doc = fitz.open(out_pdf)
    assert doc.page_count == page_count

    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    assert "Karnataka State Audit Department" in full_text
    assert "AI summary: template mode" in full_text
    assert "DEMO DATA" in full_text
    assert "RPT-2025-9999" in full_text
    assert "\u20b9" in full_text  # Unicode ₹ Rupee symbol present


def test_report_generation_and_supersession(client, auth_tokens, db_session):
    case = db_session.query(AuditCase).filter(AuditCase.case_number == "CAS-2024-KAL-005").first()
    if not case:
        case = db_session.query(AuditCase).first()
    assert case is not None

    headers = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "preliminary", "title": "Test Preliminary Audit", "includes_demo_watermark": True},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["current_version"] == 1
    assert data["status"] == "Draft"
    assert data["report_number"].startswith("RPT-")
    assert len(data["pdf_sha256"]) == 64
    rep_id = data["id"]

    # Generate version 2
    res2 = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "interim", "title": "Test Interim Audit v2", "includes_demo_watermark": True},
        headers=headers,
    )
    assert res2.status_code == 200, res2.text
    data2 = res2.json()
    assert data2["current_version"] == 2
    assert data2["id"] == rep_id

    # Verify version 1 is now Superseded
    rep_detail = client.get(f"/api/reports/{rep_id}", headers=headers).json()
    assert len(rep_detail["versions"]) >= 2
    v1 = [v for v in rep_detail["versions"] if v["version_number"] == 1][0]
    assert v1["status"] == "Superseded"


def test_final_report_blocker_gate(client, auth_tokens, db_session):
    case = db_session.query(AuditCase).first()

    # Ensure there is an open high/critical finding
    finding = db_session.query(Finding).filter(Finding.case_id == case.id).first()
    if not finding:
        finding = Finding(
            case_id=case.id,
            finding_number="FND-BLOCK-01",
            title="Unreviewed high risk expenditure",
            description="High risk flagged expenditure",
            confidence=90.0,
            risk_level="High",
            status="Open",
        )
        db_session.add(finding)
    else:
        finding.risk_level = "High"
        finding.status = "Open"
    db_session.commit()

    headers = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "final", "title": "Final Blocked Test"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "high/critical findings remain open" in res.json()["detail"]


def test_watermark_permission_guard(client, auth_tokens, db_session):
    case = db_session.query(AuditCase).first()

    # Regular Auditor cannot turn off watermark
    auditor_headers = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    res = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "preliminary", "includes_demo_watermark": False},
        headers=auditor_headers,
    )
    assert res.status_code == 403
    assert "Senior Auditors or Audit Officers" in res.json()["detail"]

    # Senior Auditor CAN turn off watermark
    senior_headers = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}
    res2 = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "preliminary", "includes_demo_watermark": False},
        headers=senior_headers,
    )
    assert res2.status_code == 200


def test_maker_checker_report_approval(client, auth_tokens, db_session):
    case = db_session.query(AuditCase).first()
    auditor_headers = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # Auditor drafts report
    gen_res = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "preliminary", "title": "Maker Checker Test"},
        headers=auditor_headers,
    )
    assert gen_res.status_code == 200
    rep_id = gen_res.json()["id"]

    # Self-approval strictly forbidden
    self_app = client.post(
        f"/api/reports/{rep_id}/approve",
        json={"comment": "Self-approval attempt"},
        headers=auditor_headers,
    )
    assert self_app.status_code in (400, 403)
    if self_app.status_code == 400:
        assert "cannot approve their own report" in self_app.json()["detail"]

    # Senior Auditor approves successfully
    senior_headers = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}
    app_res = client.post(
        f"/api/reports/{rep_id}/approve",
        json={"comment": "Approved after comprehensive scrutiny of all voucher annexures."},
        headers=senior_headers,
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "Approved"


def test_public_zero_knowledge_verification(client, auth_tokens, db_session):
    case = db_session.query(AuditCase).first()
    headers = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    gen_res = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "preliminary", "title": "Public Verify Test"},
        headers=headers,
    )
    assert gen_res.status_code == 200
    rep_num = gen_res.json()["report_number"]

    # Public GET without token
    res = client.get(f"/verify/{rep_num}")
    assert res.status_code == 200
    data = res.json()

    assert data["valid"] is True
    assert data["report_number"] == rep_num
    assert "pdf_sha256" in data

    # Zero-knowledge assertions
    assert "findings" not in data
    assert "amount" not in data
    assert "vendors" not in data
    assert "documents" not in data


def test_public_file_tamper_detection(client, auth_tokens, db_session):
    case = db_session.query(AuditCase).first()
    headers = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    gen_res = client.post(
        f"/api/cases/{case.id}/reports/generate",
        json={"report_type": "preliminary", "title": "Tamper Test"},
        headers=headers,
    )
    rep_id = gen_res.json()["id"]
    rep_num = gen_res.json()["report_number"]

    # Download authentic PDF bytes
    dl_res = client.get(f"/api/reports/{rep_id}/download", headers=headers)
    assert dl_res.status_code == 200
    valid_pdf_bytes = dl_res.content

    # 1. Verify authentic file -> MATCH
    res_match = client.post(
        f"/verify/{rep_num}/file",
        files={"file": ("report.pdf", valid_pdf_bytes, "application/pdf")},
    )
    assert res_match.status_code == 200
    assert res_match.json()["match"] is True

    # 2. Mutate 1 byte -> NO MATCH
    tampered_bytes = bytearray(valid_pdf_bytes)
    # Flip one byte near the end
    tampered_bytes[-15] = (tampered_bytes[-15] + 1) % 256
    res_tamper = client.post(
        f"/verify/{rep_num}/file",
        files={"file": ("report.pdf", bytes(tampered_bytes), "application/pdf")},
    )
    assert res_tamper.status_code == 200
    assert res_tamper.json()["match"] is False
    assert "Checksum mismatch" in res_tamper.json()["message"]


def test_banned_wording_in_reports():
    """Ensures deterministic, neutral wording: never 'fraud'."""
    banned = ["fraud", "fraudulent", "scam", "corrupt"]
    files_to_check = [
        "app/services/reporting/pdf_generator.py",
        "app/api/reports.py",
        "app/api/public_verify.py",
    ]
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for rel_path in files_to_check:
        filepath = os.path.join(base_dir, rel_path)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for w in banned:
                assert w not in content, f"Banned word '{w}' found in {filepath}"
