from decimal import Decimal
from typing import Dict, List
from app.models.financial import Vendor
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleVendorConcentration(Rule):
    id = "R-011"
    name = "Vendor Concentration & High-Frequency Repeat Spend"
    description = "Flags excessive concentration where a single vendor (including all associated name aliases) receives disproportionate share of case expenditure (>40%) or high-frequency payments (>5)."
    category = "vendor"
    default_thresholds = {
        "spend_share_threshold_pct": 50.0,
        "payment_count_threshold": 5
    }

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        spend_pct_thresh = Decimal(str(ctx.thresholds.get("spend_share_threshold_pct", self.default_thresholds["spend_share_threshold_pct"])))
        count_thresh = int(ctx.thresholds.get("payment_count_threshold", self.default_thresholds["payment_count_threshold"]))

        # Filter disbursements (use Vouchers to avoid double counting bills + vouchers + debits)
        vouchers = [r for r in ctx.records if r.record_type == "voucher" and r.total_amount > Decimal("0.00")]
        if vouchers:
            disbursements = vouchers
        else:
            disbursements = [r for r in ctx.records if r.record_type in ("bank_debit", "ledger_entry") and r.total_amount > Decimal("0.00")]
            if not disbursements:
                disbursements = [r for r in ctx.records if r.record_type == "bill" and r.total_amount > Decimal("0.00")]

        if not disbursements:
            return []

        total_case_spend = sum((d.total_amount for d in disbursements), Decimal("0.00"))
        if total_case_spend <= Decimal("0.00"):
            return []

        # Group by vendor_id
        vendor_totals: Dict[str, Decimal] = {}
        vendor_recs: Dict[str, List[any]] = {}

        for d in disbursements:
            v_id = d.vendor_id or "UNKNOWN"
            vendor_totals[v_id] = vendor_totals.get(v_id, Decimal("0.00")) + d.total_amount
            vendor_recs.setdefault(v_id, []).append(d)

        for v_id, v_amount in vendor_totals.items():
            if v_id == "UNKNOWN":
                continue

            v_count = len(vendor_recs[v_id])
            spend_share_pct = (v_amount / total_case_spend) * Decimal("100.0")

            # Look up vendor legal name
            vendor_obj = ctx.db.query(Vendor).filter(Vendor.id == v_id).first()
            vendor_name = vendor_obj.legal_name if vendor_obj else f"Vendor {v_id[:8]}"

            exceeds_share = spend_share_pct > spend_pct_thresh
            exceeds_count = v_count > count_thresh

            if exceeds_share or exceeds_count:
                evidence = [
                    {"record_id": r.id, "document_id": r.source_document_id, "document_number": r.document_number, "row": r.source_row}
                    for r in vendor_recs[v_id][:15]
                ]

                reasons = []
                if exceeds_share:
                    reasons.append(f"spend share {spend_share_pct:.1f}% exceeds threshold of {spend_pct_thresh:.1f}%")
                if exceeds_count:
                    reasons.append(f"{v_count} disbursements exceed frequency threshold of {count_thresh}")

                calc = (
                    f"Vendor '{vendor_name}' received ₹{v_amount:,.2f} across {v_count} disbursements "
                    f"({spend_share_pct:.2f}% of total case expenditure ₹{total_case_spend:,.2f}; "
                    f"threshold: {spend_pct_thresh:.1f}%, max count: {count_thresh})."
                )

                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="high",
                    title=f"High Vendor Concentration: {vendor_name}",
                    description=f"Vendor '{vendor_name}' accounts for {spend_share_pct:.2f}% of case spend across {v_count} transactions.",
                    reason=f"Public procurement anti-monopoly rules trigger audit scrutiny when: {'; '.join(reasons)}.",
                    amount_at_risk=v_amount,
                    calculation=calc,
                    evidence=evidence,
                    thresholds_used={
                        "spend_share_threshold_pct": float(spend_pct_thresh),
                        "payment_count_threshold": count_thresh
                    },
                    inputs_used={
                        "vendor_name": vendor_name,
                        "vendor_total": str(v_amount),
                        "total_case_spend": str(total_case_spend),
                        "spend_share_pct": float(spend_share_pct),
                        "disbursement_count": v_count
                    },
                    confidence=95.0
                ))

        return findings
