from decimal import Decimal
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleLargeAmount(Rule):
    id = "R-012"
    name = "High-Value Transaction Threshold"
    description = "Flags individual single disbursements exceeding the statutory high-value audit threshold (default ₹5,00,000.00)."
    category = "threshold"
    default_thresholds = {"limit": 500000.0}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        limit = Decimal(str(ctx.thresholds.get("limit", self.default_thresholds["limit"])))

        disbursements = [
            r for r in ctx.records
            if r.record_type in ("voucher", "bank_debit", "bill") and r.total_amount > limit
        ]

        for d in disbursements:
            diff = d.total_amount - limit
            calc = (
                f"Single disbursement of ₹{d.total_amount:,.2f} on {d.record_type.title()} '{d.document_number}' "
                f"exceeds the high-value statutory threshold limit of ₹{limit:,.2f} by ₹{diff:,.2f}."
            )
            findings.append(FindingCandidate(
                rule_id=self.id,
                category=self.category,
                severity="medium",
                title=f"High-Value Disbursement Exceeds ₹{limit:,.0f} Threshold",
                description=f"Transaction {d.document_number} of ₹{d.total_amount:,.2f} exceeds high-value audit threshold.",
                reason="State audit manuals require enhanced due diligence and higher-tier executive sanction for high-value payments.",
                amount_at_risk=d.total_amount,
                calculation=calc,
                evidence=[{"record_id": d.id, "document_id": d.source_document_id, "document_number": d.document_number, "row": d.source_row}],
                thresholds_used={"limit": float(limit)},
                inputs_used={"amount": str(d.total_amount), "threshold": str(limit)},
                confidence=100.0
            ))

        return findings
