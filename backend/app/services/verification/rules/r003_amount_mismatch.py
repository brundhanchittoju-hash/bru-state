from decimal import Decimal
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleAmountMismatch(Rule):
    id = "R-003"
    name = "Amount Mismatch Across Linked Documents"
    description = "Compares amounts between linked Bills, Vouchers, Ledger Entries, and Bank Debits along the expenditure chain and flags discrepancies exceeding tolerance."
    category = "reconciliation"
    default_thresholds = {"tolerance": 1.0}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        tolerance = Decimal(str(ctx.thresholds.get("tolerance", self.default_thresholds["tolerance"])))

        # Build index of records
        rec_map = {r.id: r for r in ctx.records}

        for link in ctx.links:
            # R-003 strictly validates payment chain links: Bill -> Voucher -> Bank/Ledger
            if link.link_type not in ("bill_to_voucher", "voucher_to_bank", "voucher_to_ledger"):
                continue

            src = rec_map.get(link.source_record_id)
            tgt = rec_map.get(link.target_record_id)

            if not src or not tgt:
                continue

            # Compare amounts
            diff = abs(src.total_amount - tgt.total_amount)
            if diff > tolerance:
                base_amt = min(src.total_amount, tgt.total_amount)
                diff_pct = ((diff / base_amt) * 100) if base_amt > 0 else Decimal("100.0")

                src_name = src.record_type.replace("_", " ").title()
                tgt_name = tgt.record_type.replace("_", " ").title()

                evidence = [
                    {"record_id": src.id, "document_id": src.source_document_id, "document_number": src.document_number, "row": src.source_row},
                    {"record_id": tgt.id, "document_id": tgt.source_document_id, "document_number": tgt.document_number, "row": tgt.source_row}
                ]

                calc = (
                    f"{src_name} ₹{src.total_amount:,.2f} vs {tgt_name} ₹{tgt.total_amount:,.2f} = "
                    f"difference ₹{diff:,.2f} ({diff_pct:.2f}%), tolerance ₹{tolerance:,.2f}"
                )

                severity = "high" if diff > Decimal("1000.00") else "medium"

                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity=severity,
                    title=f"Amount Mismatch: {src_name} vs {tgt_name}",
                    description=f"Recorded amount in {src_name} (₹{src.total_amount:,.2f}) differs from {tgt_name} (₹{tgt.total_amount:,.2f}) by ₹{diff:,.2f}.",
                    reason=f"Financial verification requires matching reconciliation across payment vouchers, bills, and disbursements. Discrepancy exceeds tolerance of ₹{tolerance:,.2f}.",
                    amount_at_risk=diff,
                    calculation=calc,
                    evidence=evidence,
                    thresholds_used={"tolerance": float(tolerance)},
                    inputs_used={
                        "source_type": src.record_type,
                        "source_amount": str(src.total_amount),
                        "target_type": tgt.record_type,
                        "target_amount": str(tgt.total_amount),
                        "difference": str(diff),
                        "difference_pct": float(diff_pct)
                    },
                    confidence=95.0
                ))

        return findings
