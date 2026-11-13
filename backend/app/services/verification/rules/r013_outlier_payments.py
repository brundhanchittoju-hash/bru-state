from decimal import Decimal
import statistics
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleOutlierPayments(Rule):
    id = "R-013"
    name = "Statistical Outlier Payment Detection"
    description = "Employs robust modified Z-score (median absolute deviation) and IQR analysis to detect statistical anomalies in disbursements. Requires minimum 8 samples."
    category = "statistical"
    default_thresholds = {
        "min_samples": 8,
        "modified_z_threshold": 3.5,
        "iqr_multiplier": 1.5
    }

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        min_samples = int(ctx.thresholds.get("min_samples", self.default_thresholds["min_samples"]))
        z_thresh = float(ctx.thresholds.get("modified_z_threshold", self.default_thresholds["modified_z_threshold"]))
        iqr_mult = float(ctx.thresholds.get("iqr_multiplier", self.default_thresholds["iqr_multiplier"]))

        disbursements = [
            r for r in ctx.records
            if r.record_type in ("voucher", "bank_debit", "ledger_entry") and r.total_amount > Decimal("0.00")
        ]

        # Check sample size
        if len(disbursements) < min_samples:
            # Insufficient data note: Return no findings (cleanly handled)
            return []

        amounts = [float(d.total_amount) for d in disbursements]
        med = statistics.median(amounts)
        abs_deviations = [abs(x - med) for x in amounts]
        mad = statistics.median(abs_deviations)

        # 1. Modified Z-Score evaluation
        for d in disbursements:
            amt = float(d.total_amount)
            if mad > 0:
                mod_z = (0.6745 * abs(amt - med)) / mad
            else:
                std = statistics.stdev(amounts) if len(amounts) > 1 else 1.0
                mod_z = abs(amt - med) / (std or 1.0)

            if mod_z >= z_thresh and amt > med:
                calc = (
                    f"Disbursement ₹{d.total_amount:,.2f} on {d.record_type.title()} '{d.document_number}' "
                    f"yields modified Z-score of {mod_z:.2f} (Threshold: {z_thresh:.2f}; "
                    f"Sample median: ₹{med:,.2f}; MAD: ₹{mad:,.2f}; N={len(amounts)})."
                )
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="high",
                    title="Statistical Outlier Disbursement Detected",
                    description=f"Transaction {d.document_number} of ₹{d.total_amount:,.2f} is a statistical anomaly (Z-score: {mod_z:.2f}).",
                    reason=f"Payment amount significantly deviates from the central distribution of case transactions (MAD modified Z-score >= {z_thresh:.1f}).",
                    amount_at_risk=d.total_amount,
                    calculation=calc,
                    evidence=[{"record_id": d.id, "document_id": d.source_document_id, "document_number": d.document_number, "row": d.source_row}],
                    thresholds_used={
                        "min_samples": min_samples,
                        "modified_z_threshold": z_thresh,
                        "iqr_multiplier": iqr_mult
                    },
                    inputs_used={
                        "amount": float(d.total_amount),
                        "median": med,
                        "mad": mad,
                        "modified_z": round(mod_z, 2),
                        "sample_size": len(amounts)
                    },
                    confidence=90.0
                ))

        return findings
