from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.audit_case import AuditCase
from app.models.document import Document, ExtractedField
from app.models.financial import FinancialRecord, RecordLink, Transaction, Vendor, VendorAlias
from app.models.finding import Finding
from app.models.rules import VerificationRule
from app.models.system import MandatoryDocumentChecklist, Setting
from app.models.user import Department, Role, User
from app.services.audit_trail import verify_hash_chain
from app.services.verification.records_layer import build_financial_records_for_case
from app.services.verification.record_linker import link_financial_records_for_case
from app.services.verification.risk_engine import (
    calculate_case_risk_score,
    get_risk_weights,
    DEFAULT_RISK_WEIGHTS
)
from app.services.verification.rules.registry import get_all_rules, get_rule
from app.services.verification.runner import VerificationContext, run_case_verification
from app.services.verification.vendor_matcher import (
    normalize_vendor_name,
    resolve_vendor,
    compute_vendor_similarity
)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def test_auditor(db_session: Session):
    user = db_session.query(User).filter(User.email == "senior.auditor@stateaudit.kar.gov.in").first()
    return user


# ==============================================================================
# 1. VENDOR NORMALIZATION & RAPIDFUZZ TOKEN MATCHING TESTS
# ==============================================================================

def test_normalize_vendor_name():
    assert "cauvery infra projects" in normalize_vendor_name("  M/s  Cauvery Infra Projects Pvt. Ltd. ")
    assert "chamundi electricals" in normalize_vendor_name("Sri Chamundi Electricals Enterprise,")


def test_vendor_similarity_scoring():
    # Exact / Token sort match
    score_high = compute_vendor_similarity("Cauvery Infra Projects Pvt Ltd", "Cauvery Infra Projects Limited")
    assert score_high >= 88.0

    # Distinct vendors that MUST NOT merge
    score_low = compute_vendor_similarity("Kaveri Water Works", "Cauvery Infra Projects")
    assert score_low < 85.0


def test_resolve_vendor_exact_gstin(db_session: Session):
    v = db_session.query(Vendor).filter(Vendor.legal_name == "Cauvery Infra Projects").first()
    if not v:
        v = Vendor(legal_name="Cauvery Infra Projects", gstn="29AABCC1234F1Z5", pan="AABCC1234F")
        db_session.add(v)
        db_session.commit()

    matched, conf, method = resolve_vendor(db_session, raw_name="Cauvery Works", gstin="29AABCC1234F1Z5")
    assert matched is not None
    assert matched.id == v.id
    assert method == "exact_gstin"
    assert conf == 1.0


# ==============================================================================
# 2. RISK ENGINE & WEIGHTS SUM VALIDATION TESTS
# ==============================================================================

def test_risk_weights_default_sum_is_100(db_session: Session):
    weights = get_risk_weights(db_session)
    total_weight = sum(weights.values())
    assert total_weight == 100, f"Risk factor weights must sum to exactly 100%, found: {total_weight}"


def test_risk_score_bounds_and_bands(db_session: Session):
    # Empty case should produce 0 score and Low band
    score, band, factors = calculate_case_risk_score(db_session, "test-case-id", [], Decimal("100000.00"), 0)
    assert score == 0.0
    assert band == "low"
    assert factors["missing_documents"] == 0.0
    assert factors["amount_difference"] == 0.0

    # Case with critical finding must yield Critical band (>= 85.0)
    f_crit = Finding(
        case_id="test-case-id",
        risk_level="critical",
        status="Open",
        amount_at_risk=Decimal("500000.00")
    )
    score_crit, band_crit, _ = calculate_case_risk_score(db_session, "test-case-id", [f_crit], Decimal("500000.00"), 0)
    assert score_crit >= 85.0
    assert band_crit == "critical"


# ==============================================================================
# 3. STATUTORY RULES POSITIVE & NEGATIVE UNIT TESTS
# ==============================================================================

def test_rule_r001_duplicate_payment(db_session: Session):
    rule = get_rule("R-001")
    v_id = "v-test-1"

    # Positive: Two vouchers, same vendor, same amount, same date
    r1 = FinancialRecord(id="r1", case_id="c1", vendor_id=v_id, record_type="voucher", document_number="V1", date=date(2024, 3, 10), total_amount=Decimal("50000.00"))
    r2 = FinancialRecord(id="r2", case_id="c1", vendor_id=v_id, record_type="voucher", document_number="V2", date=date(2024, 3, 10), total_amount=Decimal("50000.00"))
    
    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[r1, r2], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "R-001"
    assert findings[0].amount_at_risk == Decimal("50000.00")

    # Negative: Different vendors
    r2.vendor_id = "v-test-2"
    ctx_neg = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[r1, r2], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    assert len(rule.run(ctx_neg)) == 0


def test_rule_r002_duplicate_invoice(db_session: Session):
    rule = get_rule("R-002")
    v_id = "v-test-2"

    # Positive: Same vendor, duplicate invoice number
    b1 = FinancialRecord(id="b1", case_id="c1", vendor_id=v_id, record_type="bill", document_number="INV-99", total_amount=Decimal("10000.00"))
    b2 = FinancialRecord(id="b2", case_id="c1", vendor_id=v_id, record_type="bill", document_number="INV-99", total_amount=Decimal("10000.00"))
    
    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[b1, b2], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "R-002"
    assert findings[0].amount_at_risk == Decimal("10000.00")


def test_rule_r003_amount_mismatch(db_session: Session):
    rule = get_rule("R-003")
    b = FinancialRecord(id="b1", case_id="c1", record_type="bill", document_number="B1", total_amount=Decimal("10000.00"))
    v = FinancialRecord(id="v1", case_id="c1", record_type="voucher", document_number="V1", total_amount=Decimal("12000.00"))
    link = RecordLink(id="l1", case_id="c1", source_record_id="b1", target_record_id="v1", link_type="bill_to_voucher")

    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[b, v], links=[link], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) == 1
    assert findings[0].amount_at_risk == Decimal("2000.00")


def test_rule_r004_sanction_vs_payment(db_session: Session):
    rule = get_rule("R-004")
    s = FinancialRecord(id="s1", case_id="c1", record_type="sanction", document_number="S1", total_amount=Decimal("100000.00"))
    v = FinancialRecord(id="v1", case_id="c1", record_type="voucher", document_number="V1", total_amount=Decimal("125000.00"))

    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[s, v], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) >= 1
    assert any(f.amount_at_risk == Decimal("25000.00") for f in findings)
    assert any("₹25,000.00" in f.calculation for f in findings)


def test_rule_r005_bank_vs_bill(db_session: Session):
    rule = get_rule("R-005")
    # Bank debit of 50,000 without incoming voucher_to_bank link
    bd = FinancialRecord(id="bd1", case_id="c1", record_type="bank_debit", document_number="RTGS-1", total_amount=Decimal("50000.00"))

    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[bd], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) == 1
    assert findings[0].amount_at_risk == Decimal("50000.00")


def test_rule_r006_tax_validation(db_session: Session):
    rule = get_rule("R-006")
    # Bill with 25% GST (not statutory slab)
    b = FinancialRecord(
        id="b1",
        case_id="c1",
        record_type="bill",
        document_number="B-TAX",
        base_amount=Decimal("100000.00"),
        tax_amount=Decimal("25000.00"),
        total_amount=Decimal("125000.00"),
        raw_data_json=json.dumps({"gstin": "29AABCK6789L1Z9"})
    )
    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[b], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) >= 1
    assert any("GST" in f.title for f in findings)


def test_rule_r007_arithmetic_validation(db_session: Session):
    rule = get_rule("R-007")
    # Subtotal 1,00,000 + Tax 18,000 != Total 1,25,000
    b = FinancialRecord(
        id="b1",
        case_id="c1",
        record_type="bill",
        document_number="B-MATH",
        base_amount=Decimal("100000.00"),
        tax_amount=Decimal("18000.00"),
        total_amount=Decimal("125000.00")
    )
    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[b], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) == 1
    assert findings[0].amount_at_risk == Decimal("7000.00")


def test_rule_r010_voucher_sequence(db_session: Session):
    rule = get_rule("R-010")
    # V1 dated March 20, then V2 dated March 10 (chronological inversion)
    v1 = FinancialRecord(id="v1", case_id="c1", record_type="voucher", document_number="VOUCH-01", date=date(2024, 3, 20), total_amount=Decimal("1000.00"))
    v2 = FinancialRecord(id="v2", case_id="c1", record_type="voucher", document_number="VOUCH-02", date=date(2024, 3, 10), total_amount=Decimal("1000.00"))

    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[v1, v2], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) >= 1
    assert any("Chronological Date Inversion" in f.title for f in findings)


def test_rule_r014_split_payments(db_session: Session):
    rule = get_rule("R-014")
    v_id = "v-smurf"
    # Three payments of 4.9L within 3 days, totaling 14.7L > 5L approval limit
    v1 = FinancialRecord(id="v1", case_id="c1", vendor_id=v_id, record_type="voucher", document_number="V1", date=date(2024, 3, 1), total_amount=Decimal("490000.00"))
    v2 = FinancialRecord(id="v2", case_id="c1", vendor_id=v_id, record_type="voucher", document_number="V2", date=date(2024, 3, 2), total_amount=Decimal("490000.00"))
    v3 = FinancialRecord(id="v3", case_id="c1", vendor_id=v_id, record_type="voucher", document_number="V3", date=date(2024, 3, 3), total_amount=Decimal("490000.00"))

    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[v1, v2, v3], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) >= 1
    assert findings[0].amount_at_risk == Decimal("1470000.00")


def test_rule_r016_unusual_timing(db_session: Session):
    rule = get_rule("R-016")
    # Payment on March 31 (Sunday & Fiscal Year end rush)
    v_march31 = FinancialRecord(id="v1", case_id="c1", record_type="voucher", document_number="V-YEAR-END", date=date(2024, 3, 31), total_amount=Decimal("100000.00"))

    ctx = VerificationContext(db=db_session, case=AuditCase(id="c1", case_number="C1", financial_year="2023-24"), records=[v_march31], links=[], documents=[], transactions=[], holidays=[], thresholds=rule.default_thresholds)
    findings = rule.run(ctx)
    assert len(findings) >= 1
    assert any("Weekend" in f.title or "Year-End" in f.title for f in findings)


# ==============================================================================
# 4. IDEMPOTENCY & REVIEW PRESERVATION TESTS
# ==============================================================================

def test_runner_idempotency_second_run(db_session: Session, test_auditor):
    case = db_session.query(AuditCase).filter(AuditCase.case_number == "CAS-2024-MYS-002").first()
    assert case is not None

    count_before = db_session.query(Finding).filter(Finding.case_id == case.id, Finding.deleted_at.is_(None)).count()
    
    # Run verification a second time
    summary = run_case_verification(db_session, case.id, triggered_by_id=test_auditor.id)
    
    count_after = db_session.query(Finding).filter(Finding.case_id == case.id, Finding.deleted_at.is_(None)).count()
    assert count_before == count_after, "Idempotent re-run must not create duplicate findings"
    assert summary["findings_created"] == 0, "Second run should create 0 new findings"


def test_reviewed_finding_preservation(db_session: Session, test_auditor):
    case = db_session.query(AuditCase).filter(AuditCase.case_number == "CAS-2024-MYS-002").first()
    finding = db_session.query(Finding).filter(Finding.case_id == case.id, Finding.status == "Open").first()
    assert finding is not None

    # Auditor marks finding as Confirmed with notes
    finding.status = "Confirmed"
    finding.data_changed_since_review = False
    db_session.commit()

    # Re-run verification
    run_case_verification(db_session, case.id, triggered_by_id=test_auditor.id)

    db_session.refresh(finding)
    # Finding MUST retain its Confirmed status
    assert finding.status == "Confirmed", "Human reviewer status must be strictly preserved"


# ==============================================================================
# 5. CRYPTOGRAPHIC AUDIT TRAIL VERIFICATION TEST
# ==============================================================================

def test_audit_trail_chain_validity(db_session: Session):
    res = verify_hash_chain(db_session)
    assert res["verified"] is True, f"Cryptographic audit trail hash chain failed validation: {res.get('error')}"
