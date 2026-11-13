from datetime import timedelta
from decimal import Decimal
from typing import List
from app.models.financial import FinancialRecord
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleDuplicatePayment(Rule):
    id = "R-001"
    name = "Duplicate Payment"
    description = "Detects duplicate payments: same vendor and amount within configured window, duplicate UTR/cheque, or bill paid multiple times."
    category = "duplicate"
    default_thresholds = {"window_days": 30}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        window_days = int(ctx.thresholds.get("window_days", self.default_thresholds["window_days"]))

        payment_records = [
            r for r in ctx.records
            if r.record_type in ("voucher", "bank_debit", "ledger_entry") and r.total_amount > Decimal("0.00")
        ]

        # 1. Check duplicate payment reference / UTR / Cheque
        ref_map = {}
        for r in payment_records:
            ref = (r.payment_reference or r.cheque_number or "").strip()
            if ref and len(ref) > 3 and ref.lower() not in ("cash", "none", "na", "-"):
                ref_map.setdefault(ref, []).append(r)

        for ref, recs in ref_map.items():
            if len(recs) > 1:
                total_amt = sum(r.total_amount for r in recs)
                evidence = [
                    {"record_id": r.id, "document_id": r.source_document_id, "document_number": r.document_number, "row": r.source_row}
                    for r in recs
                ]
                calc = f"Payment reference/UTR '{ref}' appears on {len(recs)} payments totaling ₹{total_amt:,.2f}"
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="critical",
                    title="Duplicate Payment Reference Detected",
                    description=f"Same transaction reference '{ref}' was recorded across {len(recs)} distinct disbursements.",
                    reason=f"Financial control policy requires unique payment references per disbursement. '{ref}' was reused.",
                    amount_at_risk=total_amt - recs[0].total_amount,
                    calculation=calc,
                    evidence=evidence,
                    thresholds_used={"window_days": window_days},
                    inputs_used={"reference": ref, "occurrences": len(recs)},
                    confidence=100.0
                ))

        # 2. Check same vendor + same amount within window_days
        linked_pairs = set()
        for link in ctx.links:
            linked_pairs.add((link.source_record_id, link.target_record_id))
            linked_pairs.add((link.target_record_id, link.source_record_id))

        checked_pairs = set()
        for i in range(len(payment_records)):
            for j in range(i + 1, len(payment_records)):
                r1 = payment_records[i]
                r2 = payment_records[j]
                if r1.id == r2.id or (r1.id, r2.id) in checked_pairs:
                    continue

                # If r1 and r2 are linked as reconciliation counterparts (e.g. voucher & bank debit), skip
                if (r1.id, r2.id) in linked_pairs:
                    continue

                # If of different record types (voucher vs bank_debit), skip unless duplicate bank debits or duplicate vouchers
                if r1.record_type != r2.record_type:
                    continue

                if r1.vendor_id and r2.vendor_id and r1.vendor_id == r2.vendor_id:
                    if r1.total_amount == r2.total_amount:
                        if r1.date and r2.date:
                            diff_days = abs((r2.date - r1.date).days)
                            if diff_days <= window_days:
                                checked_pairs.add((r1.id, r2.id))
                                checked_pairs.add((r2.id, r1.id))
                                evidence = [
                                    {"record_id": r1.id, "document_id": r1.source_document_id, "document_number": r1.document_number, "row": r1.source_row},
                                    {"record_id": r2.id, "document_id": r2.source_document_id, "document_number": r2.document_number, "row": r2.source_row}
                                ]
                                calc = f"Payment ₹{r1.total_amount:,.2f} on {r1.date} vs Payment ₹{r2.total_amount:,.2f} on {r2.date} ({diff_days} days apart, window: {window_days} days)"
                                findings.append(FindingCandidate(
                                    rule_id=self.id,
                                    category=self.category,
                                    severity="critical",
                                    title="Potential Duplicate Payment to Vendor",
                                    description=f"Identical payment amount ₹{r1.total_amount:,.2f} disbursed to the same vendor within {diff_days} days.",
                                    reason=f"Two identical payments of ₹{r1.total_amount:,.2f} were disbursed within the {window_days}-day monitoring window.",
                                    amount_at_risk=r1.total_amount,
                                    calculation=calc,
                                    evidence=evidence,
                                    thresholds_used={"window_days": window_days},
                                    inputs_used={"vendor_id": r1.vendor_id, "amount": str(r1.total_amount), "days_apart": diff_days},
                                    confidence=95.0
                                ))

        return findings
