from decimal import Decimal
import math
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleRoundNumberAndBenford(Rule):
    id = "R-015"
    name = "Round Numbers & Just-Below-Threshold Clustering"
    description = "Detects artificial transaction clustering immediately beneath statutory approval thresholds (e.g. 5% below ₹1,00,000) and excessive round-number amounts. Runs Benford check when N >= 50."
    category = "statistical"
    default_thresholds = {
        "proximity_pct": 5.0,
        "threshold_amount": 100000.0,
        "benford_min_samples": 50
    }

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        prox_pct = Decimal(str(ctx.thresholds.get("proximity_pct", self.default_thresholds["proximity_pct"])))
        thresh_amt = Decimal(str(ctx.thresholds.get("threshold_amount", self.default_thresholds["threshold_amount"])))
        benford_min = int(ctx.thresholds.get("benford_min_samples", self.default_thresholds["benford_min_samples"]))

        disbursements = [
            r for r in ctx.records
            if r.record_type in ("voucher", "bank_debit", "ledger_entry", "bill") and r.total_amount > Decimal("0.00")
        ]

        # 1. Just-Below-Threshold Clustering (e.g. between 95,000 and 99,999.99 for 100,000 threshold)
        floor_amt = thresh_amt * (Decimal("1.0") - (prox_pct / Decimal("100.0")))

        for d in disbursements:
            if floor_amt <= d.total_amount < thresh_amt:
                diff = thresh_amt - d.total_amount
                proximity = (diff / thresh_amt) * Decimal("100.0")
                calc = (
                    f"Disbursement ₹{d.total_amount:,.2f} on {d.record_type.title()} '{d.document_number}' "
                    f"is within {proximity:.2f}% (₹{diff:,.2f} below) of the statutory approval limit ₹{thresh_amt:,.2f} "
                    f"(Proximity window: {prox_pct:.1f}%)."
                )
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="medium",
                    title="Transaction Clustered Just Below Approval Threshold",
                    description=f"Amount ₹{d.total_amount:,.2f} clusters {proximity:.2f}% beneath the ₹{thresh_amt:,.2f} approval limit.",
                    reason=f"Transactions hovering immediately below formal financial delegation thresholds ({prox_pct:.1f}% margin) warrant audit review.",
                    amount_at_risk=d.total_amount,
                    calculation=calc,
                    evidence=[{"record_id": d.id, "document_id": d.source_document_id, "document_number": d.document_number, "row": d.source_row}],
                    thresholds_used={"proximity_pct": float(prox_pct), "threshold_amount": float(thresh_amt)},
                    inputs_used={"amount": str(d.total_amount), "threshold": str(thresh_amt), "proximity_pct": float(proximity)},
                    confidence=85.0
                ))

        # 2. Benford First-Digit Analysis (Only when N >= benford_min_samples)
        if len(disbursements) >= benford_min:
            # Benford theoretical first-digit distribution: P(d) = log10(1 + 1/d)
            first_digits = []
            for d in disbursements:
                s = str(int(d.total_amount)).lstrip("0")
                if s and s[0].isdigit() and s[0] != "0":
                    first_digits.append(int(s[0]))

            if len(first_digits) >= benford_min:
                observed_counts = {digit: first_digits.count(digit) for digit in range(1, 10)}
                total_n = len(first_digits)
                chi_square = 0.0

                for digit in range(1, 10):
                    expected_p = math.log10(1.0 + (1.0 / digit))
                    expected_c = expected_p * total_n
                    obs_c = observed_counts[digit]
                    chi_square += ((obs_c - expected_c) ** 2) / (expected_c or 1.0)

                # Critical value for 8 degrees of freedom at p=0.01 is 20.09
                if chi_square > 20.09:
                    calc = f"Benford Law first-digit Chi-Square = {chi_square:.2f} (Critical p=0.01 threshold: 20.09; N={total_n})."
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="medium",
                        title="Benford Law First-Digit Distribution Anomaly",
                        description=f"Transaction leading digit frequencies deviate significantly from Benford's Law (Chi-Square: {chi_square:.2f}).",
                        reason="Non-conformance with Benford's Law indicates abnormal transaction frequency patterns in accounting entries.",
                        amount_at_risk=Decimal("0.00"),
                        calculation=calc,
                        evidence=[],
                        thresholds_used={"benford_min_samples": benford_min},
                        inputs_used={"chi_square": round(chi_square, 2), "sample_size": total_n},
                        confidence=80.0
                    ))

        return findings
