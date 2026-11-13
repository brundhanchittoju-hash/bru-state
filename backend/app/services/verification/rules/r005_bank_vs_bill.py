from decimal import Decimal
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleBankVsBill(Rule):
    id = "R-005"
    name = "Bank vs Bill / Voucher Reconciliation"
    description = "Identifies bank debits lacking matching statutory bills or vouchers, and paid bills/vouchers lacking corresponding bank debits."
    category = "reconciliation"
    default_thresholds = {}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []

        bank_records = [r for r in ctx.records if r.record_type == "bank_debit" and r.total_amount > Decimal("0.00")]
        bill_records = [r for r in ctx.records if r.record_type == "bill" and r.total_amount > Decimal("0.00")]
        voucher_records = [r for r in ctx.records if r.record_type == "voucher" and r.total_amount > Decimal("0.00")]

        # Determine which records are linked
        linked_record_ids = set()
        for link in ctx.links:
            linked_record_ids.add(link.source_record_id)
            linked_record_ids.add(link.target_record_id)

        # 1. Unlinked Bank Debits (Disbursement with no matching bill/voucher)
        for b in bank_records:
            if b.id not in linked_record_ids:
                ref_txt = b.payment_reference or b.document_number or "Unreferenced"
                date_txt = str(b.date) if b.date else "Unknown Date"
                calc = f"Bank debit ₹{b.total_amount:,.2f} (Ref: {ref_txt}) on {date_txt} has no linked Bill or approved Voucher in the audit case."
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="high",
                    title="Unreconciled Bank Debit Without Supporting Voucher / Bill",
                    description=f"Bank disbursement of ₹{b.total_amount:,.2f} recorded without linked voucher or vendor invoice.",
                    reason="Public audit guidelines mandate that every bank debit must trace directly to a verified statutory bill and payment voucher.",
                    amount_at_risk=b.total_amount,
                    calculation=calc,
                    evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number, "row": b.source_row}],
                    thresholds_used={},
                    inputs_used={"bank_amount": str(b.total_amount), "reference": ref_txt, "date": date_txt},
                    confidence=90.0
                ))

        # 2. Vouchers with no Bank Debit
        if bank_records:  # Only flag if bank records exist for the case
            for v in voucher_records:
                if v.id not in linked_record_ids:
                    date_txt = str(v.date) if v.date else "Unknown Date"
                    calc = f"Payment voucher ₹{v.total_amount:,.2f} (Voucher No: {v.document_number}) on {date_txt} has no corresponding bank debit entry."
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="medium",
                        title="Payment Voucher Lacks Reconciled Bank Debit",
                        description=f"Voucher {v.document_number} for ₹{v.total_amount:,.2f} does not match any bank account debit.",
                        reason="Disbursement voucher is not corroborated by bank statement debits within the audit scope.",
                        amount_at_risk=v.total_amount,
                        calculation=calc,
                        evidence=[{"record_id": v.id, "document_id": v.source_document_id, "document_number": v.document_number, "row": v.source_row}],
                        thresholds_used={},
                        inputs_used={"voucher_amount": str(v.total_amount), "voucher_number": v.document_number},
                        confidence=85.0
                    ))

        return findings
