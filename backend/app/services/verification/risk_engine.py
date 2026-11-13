from decimal import Decimal
import json
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.system import Setting


DEFAULT_RISK_WEIGHTS = {
    "missing_documents": 20,
    "amount_difference": 20,
    "duplicate_signals": 20,
    "vendor_concentration": 10,
    "unusual_amount": 10,
    "record_incompleteness": 10,
    "date_anomalies": 10,
}


def get_risk_weights(db: Session) -> Dict[str, int]:
    """Retrieves active risk weights from database or defaults (ensuring sum == 100)."""
    setting = db.query(Setting).filter(Setting.key == "risk_weights", Setting.deleted_at.is_(None)).first()
    if setting and setting.value_json:
        try:
            weights = json.loads(setting.value_json)
            if sum(weights.values()) == 100:
                return weights
        except Exception:
            pass
    return DEFAULT_RISK_WEIGHTS.copy()


def get_risk_band(score: float) -> str:
    """Returns risk level band based on 0-100 score:

    - Low: 0 to 29
    - Medium: 30 to 59
    - High: 60 to 84
    - Critical: 85 to 100
    """
    if score >= 85.0:
        return "critical"
    elif score >= 60.0:
        return "high"
    elif score >= 30.0:
        return "medium"
    return "low"


def calculate_case_risk_score(
    db: Session,
    case_id: str,
    findings: List[Finding],
    total_spend: Decimal,
    unlinked_records_count: int = 0
) -> Tuple[float, str, Dict[str, float]]:
    """Calculates overall case risk score (0-100) using a transparent 7-factor weighted model.

    Returns: (score, risk_band, factor_breakdown_dict)
    """
    weights = get_risk_weights(db)

    active_findings = [f for f in findings if f.status != "Dismissed" and f.status != "Auto-resolved (condition no longer detected)"]

    if not active_findings and unlinked_records_count == 0:
        breakdown = {k: 0.0 for k in weights}
        return 0.0, "low", breakdown

    # 1. Missing Documents Factor (R-008)
    missing_docs_findings = [f for f in active_findings if f.rule_id == "R-008"]
    factor_missing_docs = min(1.0, len(missing_docs_findings) * 0.35)

    # 2. Amount Difference Factor (R-003, R-004, R-007)
    recon_findings = [f for f in active_findings if f.rule_id in ("R-003", "R-004", "R-007")]
    total_recon_risk = sum((f.amount_at_risk for f in recon_findings), Decimal("0.00"))
    if total_spend > Decimal("0.00"):
        diff_ratio = float(min(Decimal("1.0"), total_recon_risk / total_spend))
    else:
        diff_ratio = 1.0 if total_recon_risk > Decimal("0.00") else 0.0
    factor_amount_diff = diff_ratio

    # 3. Duplicate Payment Signals (R-001, R-002, R-010 duplicates)
    dup_findings = [f for f in active_findings if f.rule_id in ("R-001", "R-002")]
    factor_dup = min(1.0, len(dup_findings) * 0.50)

    # 4. Vendor Concentration (R-011)
    vendor_findings = [f for f in active_findings if f.rule_id == "R-011"]
    factor_vendor = min(1.0, len(vendor_findings) * 0.50)

    # 5. Unusual Amount / Outliers (R-012, R-013, R-014, R-015)
    unusual_findings = [f for f in active_findings if f.rule_id in ("R-012", "R-013", "R-014", "R-015")]
    factor_unusual = min(1.0, len(unusual_findings) * 0.30)

    # 6. Record Incompleteness (Unlinked records, R-005, low confidence)
    recon_unlinked = [f for f in active_findings if f.rule_id == "R-005"]
    incompleteness_score = (len(recon_unlinked) * 0.3) + (min(5, unlinked_records_count) * 0.1)
    factor_incompleteness = min(1.0, incompleteness_score)

    # 7. Date Anomalies (R-009, R-016)
    date_findings = [f for f in active_findings if f.rule_id in ("R-009", "R-016")]
    factor_dates = min(1.0, len(date_findings) * 0.35)

    factors = {
        "missing_documents": round(factor_missing_docs, 3),
        "amount_difference": round(factor_amount_diff, 3),
        "duplicate_signals": round(factor_dup, 3),
        "vendor_concentration": round(factor_vendor, 3),
        "unusual_amount": round(factor_unusual, 3),
        "record_incompleteness": round(factor_incompleteness, 3),
        "date_anomalies": round(factor_dates, 3),
    }

    # Weighted sum
    weighted_score = sum(factors[k] * weights[k] for k in weights)

    # Blend with max finding severity to ensure Critical findings are reflected in band
    has_critical = any(f.risk_level == "critical" for f in active_findings)
    has_high = any(f.risk_level == "high" for f in active_findings)

    if has_critical and weighted_score < 85.0:
        weighted_score = max(weighted_score, 85.0)
    elif has_high and weighted_score < 60.0:
        weighted_score = max(weighted_score, 60.0)

    final_score = round(min(100.0, max(0.0, weighted_score)), 1)
    band = get_risk_band(final_score)

    return final_score, band, factors
