"""full_seed.py - Master Seeding Pipeline for STATE AUDIT AI.

Populates a rich, deterministic, believable demo environment across 5 Karnataka schemes,
5 Karnataka districts, 50 documents, 21 findings across all risk bands, 10 report versions,
6 users across all roles, 15 vendors, calendar events, and 14 cross-linked ground-truth anomalies.
"""
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.audit_case import AuditCase, CaseStatusHistory, ScheduledEvent
from app.models.document import Document, ExtractedField
from app.models.financial import FinancialRecord, RecordLink, Transaction, Vendor, VendorAlias
from app.models.finding import Finding, FindingClarification, FindingEvidence, FindingNote, FindingReview
from app.models.report import Report, ReportVersion
from app.models.rules import VerificationRule
from app.models.system import Holiday, MandatoryDocumentChecklist, Setting
from app.models.user import Department, Role, User
from app.seed.seed_data import seed as seed_baseline
from app.seed.seed_generators import generate_seed_report, ingest_seed_document
from app.seed.verification_fixtures import seed_verification_fixtures
from app.services.audit_trail import log_activity


def run_full_seed(db: Session = None) -> Dict[str, Any]:
    """Executes the full idempotent demo seed pipeline."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        print("\n" + "=" * 80)
        print("STATE AUDIT AI — FULL DEMO SEED PIPELINE (KARNATAKA)")
        print("=" * 80)

        # 1. Baseline Seed (Roles, Settings, Holidays, Core Departments, 4 Core Users)
        seed_baseline(db)

        # 2. Ensure Verification Fixtures for Precision/Recall Benchmark
        seed_verification_fixtures(db)

        # 3. Seed 6 Users (4 core + 2 additional field auditors)
        roles_map = {r.code: r for r in db.query(Role).all()}
        depts_map = {d.code: d for d in db.query(Department).all()}

        # Ensure all 5 demo district departments exist
        needed_depts = [
            ("ZP_MYS", "Mysuru Zilla Panchayat", "Zilla Panchayat", "Mysuru"),
            ("ZP_BEL", "Belagavi Zilla Panchayat", "Zilla Panchayat", "Belagavi"),
            ("ZP_DHA", "Dharwad Zilla Panchayat", "Zilla Panchayat", "Dharwad"),
            ("ZP_TUM", "Tumakuru Zilla Panchayat", "Zilla Panchayat", "Tumakuru"),
            ("ZP_KAL", "Kalaburagi Zilla Panchayat", "Zilla Panchayat", "Kalaburagi"),
        ]
        for code, name, dtype, dist in needed_depts:
            if code not in depts_map:
                dept = Department(code=code, name=name, type=dtype, district=dist)
                db.add(dept)
                db.commit()
                db.refresh(dept)
                depts_map[code] = dept

        users_info = [
            ("admin@stateaudit.kar.gov.in", "AdminPassword@2024", "Ramesh Kumar (Admin)", "administrator", "KSAD_HQ"),
            ("officer@stateaudit.kar.gov.in", "OfficerPassword@2024", "Suresh Patil, KAS (Audit Officer)", "audit_officer", "KSAD_HQ"),
            ("senior.auditor@stateaudit.kar.gov.in", "SeniorPassword@2024", "Vidya Hegde (Senior Auditor)", "senior_auditor", "ZP_MYS"),
            ("auditor@stateaudit.kar.gov.in", "AuditorPassword@2024", "Anand Rao (Auditor)", "auditor", "ZP_MYS"),
            ("auditor2@stateaudit.kar.gov.in", "AuditorPassword@2024", "Pooja Hegde (Auditor)", "auditor", "ZP_BEL"),
            ("auditor3@stateaudit.kar.gov.in", "AuditorPassword@2024", "Basavaraj Bommai (Auditor)", "auditor", "ZP_KAL"),
        ]
        users_map = {}
        for email, pwd, name, rcode, dcode in users_info:
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(
                    email=email,
                    hashed_password=get_password_hash(pwd),
                    full_name=name,
                    role_id=roles_map[rcode].id,
                    department_id=depts_map[dcode].id,
                    is_active=True,
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            users_map[email] = u
        print(f"[OK] Seeded {len(users_map)} Users across all roles.")

        # 4. Seed 15 Realistic Karnataka Vendors
        vendors_data = [
            ("Cauvery Infra Projects", "29AABCC1234F1Z5", "AABCC1234F", False),
            ("Chamundi Electricals & Spares", "29AABCE5678H1Z8", "AABCE5678H", False),
            ("Mysuru Borewell Services", "29AABCM9101J1Z2", "AABCM9101J", False),
            ("Nandi Construction Materials", "29AABCN2345K1Z6", "AABCN2345K", False),
            ("Karnataka Rural Infra Ltd", "29AABCK6789L1Z9", "AABCK6789L", False),
            ("Hassan Tech Supplies", "29AABCH0123M1Z3", "AABCH0123M", False),
            ("Belagavi Stone Crushers & Aggregates", "29AABCB4455N1Z1", "AABCB4455N", False),
            ("Hubballi Cement & Concrete Works", "29AABCH7788P1Z4", "AABCH7788P", False),
            ("Madhugiri Water Tech Enterprises", "29AABCM3322Q1Z7", "AABCM3322Q", False),
            ("Afzalpur Sanitation & Pipes Ltd", "29AABCA9911R1Z9", "AABCA9911R", False),
            ("Sri Manjunatha Logistics & Transport", "29AABCS8899S1Z2", "AABCS8899S", False),
            ("Tungabhadra Borewell Corp", "29AABCT1122T1Z5", "AABCT1122T", False),
            ("Sri Lakshmi Traders", "29AABCS1212U1Z8", "AABCS1212U", False),
            ("Fictitious Supplies Corp", "29INVALIDGSTIN9", "INVALIDPAN", True),
            ("Sharavathi General Contractors", "29AABCS5544V1Z3", "AABCS5544V", False),
        ]
        vendors_map = {}
        for vname, gst, pan, flagged in vendors_data:
            v = db.query(Vendor).filter(Vendor.legal_name == vname).first()
            if not v:
                v = Vendor(legal_name=vname, gstn=gst, pan=pan, is_flagged=flagged)
                db.add(v)
                db.commit()
                db.refresh(v)
            vendors_map[vname] = v

        # Aliases for Sri Lakshmi Traders
        lakshmi_v = vendors_map["Sri Lakshmi Traders"]
        aliases = ["M/s Sri Lakshmi Traders", "Sri Lakshmi Trader", "SRI LAKSHMI TRADERS"]
        for al in aliases:
            a_obj = db.query(VendorAlias).filter(VendorAlias.vendor_id == lakshmi_v.id, VendorAlias.alias_name == al).first()
            if not a_obj:
                db.add(VendorAlias(vendor_id=lakshmi_v.id, alias_name=al, confidence_score=0.95, status="confirmed"))
        db.commit()
        print(f"[OK] Seeded {len(vendors_map)} Vendors with aliases.")

        # 5. Build The 5 Statutory Audit Cases
        # ----------------------------------------------------------------------
        cases_config = [
            {
                "case_number": "CAS-2024-MYS-001",
                "title": "MGNREGA Rural Infrastructure & Desilting Audit - Bilikere GP (FY 2024-25)",
                "financial_year": "2024-25",
                "department_code": "ZP_MYS",
                "district": "Mysuru",
                "taluk": "Hunsur",
                "gram_panchayat": "Bilikere GP",
                "scheme_name": "MGNREGA",
                "audit_type": "Statutory",
                "sanctioned_amount": Decimal("4500000.00"),
                "actual_expenditure": Decimal("4320000.00"),
                "status": "review",
                "risk_level": "critical",
                "lead_email": "senior.auditor@stateaudit.kar.gov.in",
                "doc_count": 12,
                "scanned_count": 2,
            },
            {
                "case_number": "CAS-2024-BEL-002",
                "title": "Pradhan Mantri Awas Yojana (Gramin) Subsidy Verification - Chikkodi TP (FY 2024-25)",
                "financial_year": "2024-25",
                "department_code": "ZP_BEL",
                "district": "Belagavi",
                "taluk": "Chikkodi",
                "gram_panchayat": "Chikkodi TP",
                "scheme_name": "PMAY-G",
                "audit_type": "Statutory",
                "sanctioned_amount": Decimal("7500000.00"),
                "actual_expenditure": Decimal("6850000.00"),
                "status": "verification",
                "risk_level": "high",
                "lead_email": "auditor@stateaudit.kar.gov.in",
                "doc_count": 8,
                "scanned_count": 1,
            },
            {
                "case_number": "CAS-2023-DHA-003",
                "title": "15th Finance Commission Untied Grants Statutory Audit - Kundgol TP (FY 2023-24)",
                "financial_year": "2023-24",
                "department_code": "ZP_DHA",
                "district": "Dharwad",
                "taluk": "Kundgol",
                "gram_panchayat": "Kundgol TP",
                "scheme_name": "15th Finance Commission Grants",
                "audit_type": "Statutory",
                "sanctioned_amount": Decimal("12000000.00"),
                "actual_expenditure": Decimal("11840000.00"),
                "status": "approved",
                "risk_level": "high",
                "lead_email": "senior.auditor@stateaudit.kar.gov.in",
                "doc_count": 15,
                "scanned_count": 2,
            },
            {
                "case_number": "CAS-2023-TUM-004",
                "title": "Jal Jeevan Mission Rural Piped Water Scheme Audit - Madhugiri TP (FY 2023-24)",
                "financial_year": "2023-24",
                "department_code": "ZP_TUM",
                "district": "Tumakuru",
                "taluk": "Madhugiri",
                "gram_panchayat": "Madhugiri TP",
                "scheme_name": "Jal Jeevan Mission",
                "audit_type": "Statutory",
                "sanctioned_amount": Decimal("25000000.00"),
                "actual_expenditure": Decimal("24780000.00"),
                "status": "closed",
                "risk_level": "medium",
                "lead_email": "officer@stateaudit.kar.gov.in",
                "doc_count": 10,
                "scanned_count": 1,
            },
            {
                "case_number": "CAS-2024-KAL-005",
                "title": "Swachh Bharat Mission (Gramin) Solid Waste Infrastructure - Afzalpur TP (FY 2024-25)",
                "financial_year": "2024-25",
                "department_code": "ZP_KAL",
                "district": "Kalaburagi",
                "taluk": "Afzalpur",
                "gram_panchayat": "Afzalpur TP",
                "scheme_name": "Swachh Bharat Mission (Gramin)",
                "audit_type": "Statutory",
                "sanctioned_amount": Decimal("3500000.00"),
                "actual_expenditure": Decimal("3200000.00"),
                "status": "documents_uploaded",
                "risk_level": "low",
                "lead_email": "auditor2@stateaudit.kar.gov.in",
                "doc_count": 5,
                "scanned_count": 0,
            },
        ]

        seeded_cases = {}
        for cdata in cases_config:
            c = db.query(AuditCase).filter(AuditCase.case_number == cdata["case_number"]).first()
            if not c:
                c = AuditCase(
                    case_number=cdata["case_number"],
                    title=cdata["title"],
                    financial_year=cdata["financial_year"],
                    department_id=depts_map[cdata["department_code"]].id,
                    district=cdata["district"],
                    taluk=cdata["taluk"],
                    gram_panchayat=cdata["gram_panchayat"],
                    scheme_name=cdata["scheme_name"],
                    audit_type=cdata["audit_type"],
                    sanctioned_amount=cdata["sanctioned_amount"],
                    actual_expenditure=cdata["actual_expenditure"],
                    status=cdata["status"],
                    risk_level=cdata["risk_level"],
                    lead_auditor_id=users_map[cdata["lead_email"]].id,
                    scope_notes=f"Statutory financial audit of {cdata['scheme_name']} implementation in {cdata['district']}.",
                )
                db.add(c)
                db.commit()
                db.refresh(c)
            else:
                c.status = cdata["status"]
                c.risk_level = cdata["risk_level"]
                c.sanctioned_amount = cdata["sanctioned_amount"]
                c.actual_expenditure = cdata["actual_expenditure"]
                db.commit()
            seeded_cases[cdata["case_number"]] = c
        print(f"[OK] Seeded 5 Master Audit Cases across Karnataka districts.")

        # 6. Seed ~50 Real Statutory Documents Across Cases
        # ----------------------------------------------------------------------
        total_docs_created = 0

        # Helper to generate doc set
        def seed_docs_for_case(case_obj: AuditCase, count: int, scanned_count: int, prefix: str):
            nonlocal total_docs_created
            # Document templates
            doc_specs = [
                ("Admin Sanction Order", f"AS-{prefix}-01.pdf", "Sanction Order", {"sanction_no": f"AS/{prefix}/2024/01", "sanction_date": "2024-04-05", "sanctioned_amount": str(case_obj.sanctioned_amount)}),
                ("Technical Sanction Order", f"TS-{prefix}-01.pdf", "Sanction Order", {"ts_no": f"TS/{prefix}/2024/02", "estimate_amount": str(case_obj.sanctioned_amount)}),
                ("Work Order WO-01", f"WO-{prefix}-01.pdf", "Work Order", {"work_order_no": f"WO/{prefix}/01", "order_date": "2024-05-10", "contractor": "Cauvery Infra Projects"}),
                ("Measurement Book Extract MB-01", f"MB-{prefix}-01.pdf", "Measurement Book", {"mb_no": f"MB-44/{prefix}", "recorded_value": "450000.00"}),
                ("Completion Certificate CC-01", f"CC-{prefix}-01.pdf", "Completion Certificate", {"cert_no": f"CC/{prefix}/01", "inspection_date": "2024-08-20"}),
                ("Tax Invoice INV-101", f"INV-{prefix}-101.pdf", "Tax Invoice", {"bill_number": f"INV-{prefix}-101", "bill_date": "2024-06-15", "amount": "485000.00"}),
                ("Payment Voucher VR-101", f"VR-{prefix}-101.pdf", "Payment Voucher", {"voucher_no": f"VR-{prefix}-101", "payment_date": "2024-06-20", "amount": "485000.00"}),
                ("Tax Invoice INV-102", f"INV-{prefix}-102.pdf", "Tax Invoice", {"bill_number": f"INV-{prefix}-102", "bill_date": "2024-07-10", "amount": "320000.00"}),
                ("Payment Voucher VR-102", f"VR-{prefix}-102.pdf", "Payment Voucher", {"voucher_no": f"VR-{prefix}-102", "payment_date": "2024-07-15", "amount": "320000.00"}),
                ("Bank Passbook Extract", f"BANK-{prefix}.pdf", "Bank Statement", {"account_no": "987654321012", "statement_period": "2024-04 to 2024-09"}),
                ("Muster Roll Register", f"MUSTER-{prefix}.pdf", "Muster Roll", {"muster_no": f"MR/{prefix}/01", "total_wages": "185000.00"}),
                ("Utilization Certificate UC-01", f"UC-{prefix}-01.pdf", "Utilization Certificate", {"uc_no": f"UC/{prefix}/2024", "expenditure": str(case_obj.actual_expenditure)}),
                ("Material Receipt Note MRN-01", f"MRN-{prefix}-01.pdf", "Material Receipt", {"mrn_no": f"MRN/{prefix}/01", "supplier": "Nandi Construction Materials"}),
                ("Tender Notification NIT-01", f"NIT-{prefix}-01.pdf", "Tender", {"tender_no": f"NIT/{prefix}/2024/T-01", "estimated_cost": str(case_obj.sanctioned_amount)}),
                ("Comparative Statement CS-01", f"CS-{prefix}-01.pdf", "Comparative Statement", {"cs_no": f"CS/{prefix}/01", "lowest_bidder": "Cauvery Infra Projects"}),
            ]

            scanned_left = scanned_count
            for i in range(min(count, len(doc_specs))):
                title, fname, dtype, flds = doc_specs[i]
                is_scanned = False
                if scanned_left > 0 and dtype in ("Payment Voucher", "Measurement Book", "Completion Certificate"):
                    is_scanned = True
                    scanned_left -= 1

                lines = [
                    f"Official Audit Record: {title}",
                    f"Scheme: {case_obj.scheme_name} | District: {case_obj.district}",
                    f"Document Ref: {fname}",
                    "Certified copy verified against Panchayat Raj statutory accounts.",
                    "All disbursements executed under Karnataka Transparency in Public Procurements Act.",
                ]
                ingest_seed_document(
                    db=db,
                    case_id=case_obj.id,
                    title=f"{case_obj.case_number} - {title}",
                    filename=f"{case_obj.case_number}_{fname}",
                    doc_type=dtype,
                    fields=flds,
                    lines=lines,
                    is_scanned=is_scanned,
                )
                total_docs_created += 1

        seed_docs_for_case(seeded_cases["CAS-2024-MYS-001"], 12, 2, "MYS")
        seed_docs_for_case(seeded_cases["CAS-2024-BEL-002"], 8, 1, "BEL")
        seed_docs_for_case(seeded_cases["CAS-2023-DHA-003"], 15, 2, "DHA")
        seed_docs_for_case(seeded_cases["CAS-2023-TUM-004"], 10, 1, "TUM")
        seed_docs_for_case(seeded_cases["CAS-2024-KAL-005"], 5, 0, "KAL")
        print(f"[OK] Seeded {total_docs_created} Statutory Documents with 6 scanned-style pages.")

        # 7. Seed 21 Findings Across All Risk Bands & States
        # ----------------------------------------------------------------------
        rules_map = {r.rule_code: r for r in db.query(VerificationRule).all()}

        findings_specs = [
            # Case 1: Mysuru (6 findings across risk bands and states)
            ("CAS-2024-MYS-001", "R-001", "Exact duplicate payment detected on Voucher VOUCH-2024-094", "critical", "Confirmed", Decimal("185000.00"), Decimal("185000.00"), 98.5),
            ("CAS-2024-MYS-001", "R-002", "Duplicate invoice number INV-2024-781 reused across payments", "high", "Pending Approval", Decimal("420000.00"), Decimal("420000.00"), 92.0),
            ("CAS-2024-MYS-001", "R-003", "Amount mismatch: supporting bill ₹85,000 paid as ₹95,000", "high", "Needs Clarification", Decimal("10000.00"), Decimal("10000.00"), 88.0),
            ("CAS-2024-MYS-001", "R-004", "Cumulative disbursements exceed administrative sanction AS-01", "critical", "Escalated", Decimal("240000.00"), Decimal("240000.00"), 99.0),
            ("CAS-2024-MYS-001", "R-005", "Unreconciled bank debit of ₹5,50,000 without matching voucher", "critical", "Confirmed", Decimal("550000.00"), Decimal("550000.00"), 95.0),
            ("CAS-2024-MYS-001", "R-012", "Disbursement exceeding statutory cash limit: ₹45,000 paid in cash", "high", "Auto-resolved", Decimal("45000.00"), Decimal("45000.00"), 90.0),

            # Case 2: Belagavi (4 findings)
            ("CAS-2024-BEL-002", "R-006", "Statutory GST slab variance detected in supplier tax invoice", "high", "Open", Decimal("7000.00"), Decimal("7000.00"), 85.0),
            ("CAS-2024-BEL-002", "R-007", "Line items arithmetic does not tally with bill total on INV-940", "medium", "Open", Decimal("14000.00"), Decimal("14000.00"), 82.0),
            ("CAS-2024-BEL-002", "R-008", "Mandatory measurement book missing for civil works milestone", "high", "Open", Decimal("0.00"), Decimal("0.00"), 94.0),
            ("CAS-2024-BEL-002", "R-003", "Voucher amount ₹1,80,000 exceeds bill amount ₹1,62,000", "medium", "Open", Decimal("18000.00"), Decimal("18000.00"), 87.0),

            # Case 3: Dharwad (8 findings - all reviewed)
            ("CAS-2023-DHA-003", "R-009", "Payment disbursement date precedes administrative sanction order", "medium", "Confirmed", Decimal("500000.00"), Decimal("500000.00"), 91.0),
            ("CAS-2023-DHA-003", "R-010", "Voucher numbering sequence gap between VR-310 and VR-315", "medium", "Confirmed", Decimal("0.00"), Decimal("0.00"), 89.0),
            ("CAS-2023-DHA-003", "R-011", "High vendor spend concentration exceeding 70% of total grant", "medium", "Dismissed", Decimal("0.00"), Decimal("0.00"), 78.0),
            ("CAS-2023-DHA-003", "R-014", "Split procurement payments below ₹5,00,000 statutory tender limit", "high", "Confirmed", Decimal("1470000.00"), Decimal("1470000.00"), 96.0),
            ("CAS-2023-DHA-003", "R-015", "Unusual round sum payment pattern in supplier disbursements", "medium", "Confirmed", Decimal("980000.00"), Decimal("980000.00"), 84.0),
            ("CAS-2023-DHA-003", "R-016", "Disbursement processed on Sunday / gazetted public holiday", "low", "Confirmed", Decimal("0.00"), Decimal("0.00"), 99.0),
            ("CAS-2023-DHA-003", "R-001", "Secondary duplicate payment on civil material supplier invoice", "high", "Confirmed", Decimal("65000.00"), Decimal("65000.00"), 93.0),
            ("CAS-2023-DHA-003", "R-007", "Minor rounding variation in tax computation on supplier bill", "low", "Auto-resolved", Decimal("5000.00"), Decimal("5000.00"), 80.0),

            # Case 4: Tumakuru (3 findings - confirmed and closed)
            ("CAS-2023-TUM-004", "R-013", "Statistical IQR outlier payment detected in water supply pipeline works", "high", "Confirmed", Decimal("1250000.00"), Decimal("1250000.00"), 92.0),
            ("CAS-2023-TUM-004", "R-006", "Incorrect HSN tax rate applied on pipeline valve fittings", "medium", "Confirmed", Decimal("12000.00"), Decimal("12000.00"), 86.0),
            ("CAS-2023-TUM-004", "R-003", "Disbursement variance against pipe laying contractor bill", "medium", "Confirmed", Decimal("25000.00"), Decimal("25000.00"), 88.0),

            # Case 5: Kalaburagi has 0 findings (clean benchmark!)
        ]

        f_counter = 1
        created_findings = []
        for c_no, r_code, title, r_level, st, amt, risk_amt, conf in findings_specs:
            case_obj = seeded_cases[c_no]
            rule_obj = rules_map.get(r_code)
            f_num = f"F-2024-{f_counter:04d}"
            f_counter += 1

            f_obj = db.query(Finding).filter(Finding.case_id == case_obj.id, Finding.title == title).first()
            if not f_obj:
                f_obj = Finding(
                    case_id=case_obj.id,
                    rule_id=rule_obj.id if rule_obj else None,
                    finding_number=f_num,
                    category="procurement" if r_code in ("R-014", "R-008") else ("compliance" if r_code in ("R-006", "R-009", "R-010", "R-016") else "financial"),
                    title=title,
                    description=f"Statutory rule {r_code} verification flagged this transaction for auditor review: {title}.",
                    reason=f"Verification rule {r_code} triggered against statutory threshold.",
                    calculation=f"Amount evaluated: INR {amt:,.2f}; Threshold variance: INR {risk_amt:,.2f}",
                    risk_level=r_level,
                    status=st,
                    financial_implication=amt,
                    amount_at_risk=risk_amt,
                    confidence=conf,
                    assigned_auditor_id=users_map["senior.auditor@stateaudit.kar.gov.in"].id,
                )
                db.add(f_obj)
                db.commit()
                db.refresh(f_obj)
            else:
                f_obj.status = st
                f_obj.risk_level = r_level
                db.commit()

            # Add reviews and notes for realistic audit lifecycle
            if st in ("Confirmed", "Dismissed", "Pending Approval", "Escalated"):
                rev = db.query(FindingReview).filter(FindingReview.finding_id == f_obj.id).first()
                if not rev:
                    rev = FindingReview(
                        finding_id=f_obj.id,
                        reviewer_id=users_map["senior.auditor@stateaudit.kar.gov.in"].id,
                        reviewer_role="Senior Auditor",
                        action="reviewed",
                        comments=f"Finding verified against physical records; status updated to {st}.",
                        previous_status="Open",
                        new_status=st,
                    )
                    db.add(rev)
                    db.commit()

            if st == "Needs Clarification":
                clar = db.query(FindingClarification).filter(FindingClarification.finding_id == f_obj.id).first()
                if not clar:
                    clar = FindingClarification(
                        finding_id=f_obj.id,
                        requested_by_id=users_map["auditor@stateaudit.kar.gov.in"].id,
                        question="Please provide the measurement book page certifying the extra ₹10,000 billed.",
                        status="pending",
                    )
                    db.add(clar)
                    db.commit()

            created_findings.append(f_obj)
        print(f"[OK] Seeded {len(created_findings)} Statutory Findings across all risk bands and states.")

        # 8. Seed 10+ Report Versions Across Cases
        # ----------------------------------------------------------------------
        reports_created = []

        # Case 1 (Mysuru): v1 Draft (Superseded), v2 Final (Approved)
        r1_v1 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2024-MYS-001"],
            report_number="RPT-2024-MYS-0001",
            title="MGNREGA Statutory Audit Draft Report - Bilikere GP",
            version_no=1,
            status="Superseded",
            generator_user=users_map["auditor@stateaudit.kar.gov.in"],
            watermark=True,
        )
        r1_v2 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2024-MYS-001"],
            report_number="RPT-2024-MYS-0001",
            title="MGNREGA Statutory Audit Final Report - Bilikere GP",
            version_no=2,
            status="Approved",
            generator_user=users_map["senior.auditor@stateaudit.kar.gov.in"],
            approver_user=users_map["officer@stateaudit.kar.gov.in"],
            watermark=True,
        )
        # Preliminary draft report for Mysuru
        r1_b = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2024-MYS-001"],
            report_number="RPT-2024-MYS-0002",
            title="MGNREGA Interim Field Audit Observations",
            version_no=1,
            status="Draft",
            generator_user=users_map["auditor@stateaudit.kar.gov.in"],
            watermark=True,
        )

        # Case 2 (Belagavi): v1 Draft
        r2_v1 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2024-BEL-002"],
            report_number="RPT-2024-BEL-0001",
            title="PMAY-G Housing Subsidy Preliminary Audit Findings",
            version_no=1,
            status="Draft",
            generator_user=users_map["auditor@stateaudit.kar.gov.in"],
            watermark=True,
        )
        r2_v2 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2024-BEL-002"],
            report_number="RPT-2024-BEL-0002",
            title="PMAY-G Beneficiary Disbursement Sample Audit",
            version_no=1,
            status="Draft",
            generator_user=users_map["auditor2@stateaudit.kar.gov.in"],
            watermark=True,
        )

        # Case 3 (Dharwad): v1 Draft (Superseded), v2 Final (Superseded), v3 Approved
        r3_v1 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2023-DHA-003"],
            report_number="RPT-2023-DHA-0001",
            title="15th FC Untied Grants Audit Draft Report - Kundgol TP",
            version_no=1,
            status="Superseded",
            generator_user=users_map["auditor@stateaudit.kar.gov.in"],
            watermark=True,
        )
        r3_v2 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2023-DHA-003"],
            report_number="RPT-2023-DHA-0001",
            title="15th FC Untied Grants Audit Revised Draft Report",
            version_no=2,
            status="Superseded",
            generator_user=users_map["senior.auditor@stateaudit.kar.gov.in"],
            watermark=True,
        )
        r3_v3 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2023-DHA-003"],
            report_number="RPT-2023-DHA-0001",
            title="15th FC Untied Grants Statutory Audit Final Report - Kundgol TP",
            version_no=3,
            status="Approved",
            generator_user=users_map["senior.auditor@stateaudit.kar.gov.in"],
            approver_user=users_map["officer@stateaudit.kar.gov.in"],
            watermark=True,
        )

        # Case 4 (Tumakuru): v1 Draft (Superseded), v2 Approved
        r4_v1 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2023-TUM-004"],
            report_number="RPT-2023-TUM-0001",
            title="Jal Jeevan Mission Audit Initial Findings Report",
            version_no=1,
            status="Superseded",
            generator_user=users_map["auditor@stateaudit.kar.gov.in"],
            watermark=True,
        )
        r4_v2 = generate_seed_report(
            db=db,
            case=seeded_cases["CAS-2023-TUM-004"],
            report_number="RPT-2023-TUM-0001",
            title="Jal Jeevan Mission Statutory Audit Completion Report - Madhugiri TP",
            version_no=2,
            status="Approved",
            generator_user=users_map["senior.auditor@stateaudit.kar.gov.in"],
            approver_user=users_map["officer@stateaudit.kar.gov.in"],
            watermark=True,
        )

        all_report_versions = [r1_v1, r1_v2, r1_b, r2_v1, r2_v2, r3_v1, r3_v2, r3_v3, r4_v1, r4_v2]
        print(f"[OK] Seeded {len(all_report_versions)} Statutory Report Versions with DEMO watermarks & SHA-256 seals.")

        # 9. Seed 20+ Scheduled Calendar Events
        # ----------------------------------------------------------------------
        events_data = [
            ("Entry Conference: MGNREGA Audit", date(2024, 4, 15), "CAS-2024-MYS-001", "hearing", "Preliminary audit entry conference with GP officials"),
            ("Physical Verification of Water Works", date(2024, 5, 20), "CAS-2024-MYS-001", "review", "Field inspection of Bilikere desilting tanks"),
            ("Voucher & Cash Book Audit Meeting", date(2024, 6, 25), "CAS-2024-MYS-001", "audit_deadline", "Substantive testing of Bilikere GP payment vouchers"),
            ("Maker-Checker Audit Sign-off", date(2024, 7, 10), "CAS-2024-MYS-001", "review", "Senior Auditor review of flagged findings"),
            ("Exit Conference & Report Discussion", date(2024, 7, 28), "CAS-2024-MYS-001", "submission", "Exit conference and submission of Draft Report v1"),
            ("Entry Conference: PMAY-G Subsidy Audit", date(2024, 5, 2), "CAS-2024-BEL-002", "hearing", "Introductory meeting with Chikkodi Taluk Executive Officer"),
            ("Geo-tag Physical House Verification", date(2024, 6, 12), "CAS-2024-BEL-002", "review", "Sample inspection of 25 beneficiary houses in Arabhavi"),
            ("Beneficiary Account Statement Reconciliation", date(2024, 7, 18), "CAS-2024-BEL-002", "audit_deadline", "Reconciliation of direct benefit transfers with bank ledger"),
            ("Interim Observations Meeting", date(2024, 8, 14), "CAS-2024-BEL-002", "submission", "Submission of PMAY-G preliminary findings"),
            ("Entry Conference: 15th FC Grants", date(2023, 5, 10), "CAS-2023-DHA-003", "hearing", "Statutory audit entry conference at Kundgol TP"),
            ("Tender & Contract File Verification", date(2023, 6, 15), "CAS-2023-DHA-003", "review", "KTTP compliance check on civil tenders"),
            ("Measurement Book Field Inspection", date(2023, 7, 22), "CAS-2023-DHA-003", "review", "Joint measurement of road asphalt works"),
            ("Finding Clarification Hearing", date(2023, 9, 14), "CAS-2023-DHA-003", "hearing", "Taluk Panchayat response on split procurement notices"),
            ("Final Report Release & PAC Submission", date(2023, 11, 20), "CAS-2023-DHA-003", "submission", "Statutory release of Approved Report v3"),
            ("Entry Conference: Jal Jeevan Mission", date(2023, 6, 5), "CAS-2023-TUM-004", "hearing", "District water supply division entry briefing"),
            ("Pipeline Pressure Test Inspection", date(2023, 7, 12), "CAS-2023-TUM-004", "review", "Physical verification of pipeline network in Honnavalli"),
            ("Voucher & RTGS Reconciliation", date(2023, 8, 20), "CAS-2023-TUM-004", "audit_deadline", "Bank statement reconciliation against Treasury debits"),
            ("Audit Settlement & Closing Conference", date(2023, 10, 15), "CAS-2023-TUM-004", "submission", "Case closing and settlement of audit paras"),
            ("Entry Conference: SBM-G Sanitation", date(2024, 8, 1), "CAS-2024-KAL-005", "hearing", "Afzalpur solid waste management audit entry"),
            ("Solid Waste Treatment Facility Visit", date(2024, 9, 10), "CAS-2024-KAL-005", "review", "Physical site inspection of compost and waste units"),
            ("Annual State Audit Conference 2025", date(2025, 2, 15), None, "hearing", "Karnataka State Audit Officers Annual Review Conference"),
        ]
        created_events_count = 0
        for title, edate, c_no, etype, desc in events_data:
            c_obj = seeded_cases.get(c_no) if c_no else None
            ev = db.query(ScheduledEvent).filter(ScheduledEvent.title == title, ScheduledEvent.event_date == edate).first()
            if not ev:
                ev = ScheduledEvent(
                    title=title,
                    event_date=edate,
                    case_id=c_obj.id if c_obj else None,
                    created_by_id=users_map["senior.auditor@stateaudit.kar.gov.in"].id,
                    description=desc,
                    event_type=etype,
                )
                db.add(ev)
                created_events_count += 1
        db.commit()
        print(f"[OK] Seeded {created_events_count} Scheduled Calendar Events.")

        # 10. Audit Trail Genesis & Completion Entries
        log_activity(
            db=db,
            action="seed:full_complete",
            entity_type="system",
            entity_id="state_audit_full_seed",
            actor_name="System Seeder",
            payload={
                "cases_count": len(seeded_cases),
                "docs_count": total_docs_created,
                "findings_count": len(created_findings),
                "reports_count": len(all_report_versions),
                "users_count": len(users_map),
                "vendors_count": len(vendors_map),
            },
        )

        return {
            "cases_count": len(seeded_cases),
            "documents_count": total_docs_created,
            "findings_count": len(created_findings),
            "report_versions_count": len(all_report_versions),
            "users_count": len(users_map),
            "vendors_count": len(vendors_map),
            "events_count": created_events_count,
        }

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Full seed pipeline error: {e}")
        raise e
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    run_full_seed()
