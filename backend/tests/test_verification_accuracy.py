import json
import os
import pytest
from app.core.database import SessionLocal
from app.models.audit_case import AuditCase
from app.models.finding import Finding
from app.models.rules import VerificationRule


@pytest.fixture(scope="module")
def ground_truth():
    gt_path = os.path.join(os.path.dirname(__file__), "verification_ground_truth.json")
    with open(gt_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_verification_accuracy_benchmark(ground_truth):
    """Ground truth benchmark:

    Evaluates that all 13 intentional anomalies in CAS-2024-MYS-002 are detected,
    and that clean case CAS-2024-MYS-003 produces 0 High/Critical false positives.
    Computes precision, recall, and F1 score.
    """
    db = SessionLocal()
    try:
        # 1. Evaluate CAS-2024-MYS-002 (Anomalies Case)
        case_002 = db.query(AuditCase).filter(AuditCase.case_number == ground_truth["test_case_anomalies"]).first()
        assert case_002 is not None, "Fixture case CAS-2024-MYS-002 not found. Run verification_fixtures seed first."

        r_map = {r.id: r.rule_code for r in db.query(VerificationRule).all()}
        findings_002 = db.query(Finding).filter(
            Finding.case_id == case_002.id,
            Finding.deleted_at.is_(None)
        ).all()

        detected_rules = {r_map.get(f.rule_id, f.rule_id) for f in findings_002}

        # Check each of the 13 intentional anomalies
        anomalies = ground_truth["anomalies"]
        detected_anomalies_count = 0
        missing_anomalies = []

        print("\n" + "=" * 80)
        print("VERIFICATION ENGINE ACCURACY BENCHMARK - CAS-2024-MYS-002")
        print("=" * 80)

        for anom in anomalies:
            rule_id = anom["rule_id"]
            if rule_id in detected_rules:
                detected_anomalies_count += 1
                # Find matching finding
                matching = [f for f in findings_002 if r_map.get(f.rule_id, f.rule_id) == rule_id]
                print(f"[PASS] Anomaly #{anom['anomaly_id']:02d} ({rule_id}): {anom['name']} -> Detected ({len(matching)} findings, sample: '{matching[0].title}')")
            else:
                missing_anomalies.append(anom)
                print(f"[FAIL] Anomaly #{anom['anomaly_id']:02d} ({rule_id}): {anom['name']} -> NOT DETECTED")

        recall = (detected_anomalies_count / len(anomalies)) * 100.0
        print(f"\nAnomaly Detection Recall: {detected_anomalies_count}/{len(anomalies)} ({recall:.1f}%)")

        assert detected_anomalies_count == len(anomalies), f"Missing anomalies: {missing_anomalies}"
        assert case_002.risk_level.lower() in ("critical", "high"), f"Case 002 risk band was {case_002.risk_level}, expected Critical/High"

        # 2. Evaluate CAS-2024-MYS-003 (Clean Case)
        case_003 = db.query(AuditCase).filter(AuditCase.case_number == ground_truth["test_case_clean"]).first()
        assert case_003 is not None, "Clean fixture case CAS-2024-MYS-003 not found."

        findings_003 = db.query(Finding).filter(
            Finding.case_id == case_003.id,
            Finding.deleted_at.is_(None)
        ).all()

        high_critical_003 = [
            f for f in findings_003
            if f.risk_level and f.risk_level.lower() in ("high", "critical") and f.status != "Dismissed"
        ]

        print("\n" + "=" * 80)
        print("CLEAN BENCHMARK VERIFICATION - CAS-2024-MYS-003")
        print("=" * 80)
        print(f"Total findings: {len(findings_003)}")
        print(f"High/Critical findings: {len(high_critical_003)} (Expected: 0)")
        print(f"Risk level: {case_003.risk_level} (Expected: low)")

        assert len(high_critical_003) == 0, f"False positives detected on clean case: {[f.title for f in high_critical_003]}"
        assert case_003.risk_level.lower() == "low", f"Clean case risk band was {case_003.risk_level}, expected low"

        # Precision & F1 score calculation
        # True Positives: 13, False Negatives: 0, False Positives (high/critical on clean): 0
        tp = detected_anomalies_count
        fp = len(high_critical_003)
        fn = len(anomalies) - detected_anomalies_count
        precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        print(f"\nFinal Accuracy Metrics:")
        print(f"  Precision: {precision:.1f}%")
        print(f"  Recall:    {recall:.1f}%")
        print(f"  F1-Score:  {f1_score:.1f}%")
        print("=" * 80 + "\n")

        assert precision == 100.0
        assert recall == 100.0
        assert f1_score == 100.0

    finally:
        db.close()


def test_seed_ground_truth_catalog_and_clean_case():
    """Validates the 14 intentional anomalies documented in seed_ground_truth.json

    and checks that clean case CAS-2024-KAL-005 has 0 High/Critical findings.
    """
    gt_path = os.path.join(os.path.dirname(__file__), "..", "app", "seed", "seed_ground_truth.json")
    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    db = SessionLocal()
    try:
        # 1. Check clean case
        clean_exp = gt_data["clean_case_expectations"]
        clean_case = db.query(AuditCase).filter(AuditCase.case_number == clean_exp["case_number"]).first()
        assert clean_case is not None, f"Clean benchmark case {clean_exp['case_number']} not found."

        clean_findings = db.query(Finding).filter(
            Finding.case_id == clean_case.id,
            Finding.deleted_at.is_(None)
        ).all()
        high_crit = [f for f in clean_findings if f.risk_level and f.risk_level.lower() in ("high", "critical")]
        assert len(high_crit) <= clean_exp["max_high_findings"], f"Expected 0 high findings, found {len(high_crit)}"
        assert clean_case.risk_level.lower() == clean_exp["expected_risk_band"].lower()

        # 2. Check 14 anomalies
        r_map = {r.id: r.rule_code for r in db.query(VerificationRule).all()}
        for anom in gt_data["anomalies"]:
            c_no = anom["case_number"]
            case_obj = db.query(AuditCase).filter(AuditCase.case_number == c_no).first()
            assert case_obj is not None, f"Case {c_no} not found for anomaly {anom['anomaly_id']}"
            findings = db.query(Finding).filter(Finding.case_id == case_obj.id, Finding.deleted_at.is_(None)).all()
            matching = [f for f in findings if r_map.get(f.rule_id) == anom["rule_id"]]
            assert len(matching) > 0, f"Expected anomaly {anom['anomaly_id']} ({anom['rule_id']}) in case {c_no}, but none found."
    finally:
        db.close()
