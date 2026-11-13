from datetime import timedelta
from decimal import Decimal
from typing import Dict, List
from app.models.financial import Vendor
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleSplitPayments(Rule):
    id = "R-014"
    name = "Split Payment Evasion Below Approval Threshold"
    description = "Detects structured transactions: multiple payments to the same vendor within a time window, each individually beneath statutory approval ceiling, while their aggregate exceeds the threshold."
    category = "threshold"
    default_thresholds = {
        "window_days": 15,
        "approval_limit": 500000.0
    }

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        window_days = int(ctx.thresholds.get("window_days", self.default_thresholds["window_days"]))
        approval_limit = Decimal(str(ctx.thresholds.get("approval_limit", self.default_thresholds["approval_limit"])))

        vouchers = [
            r for r in ctx.records
            if r.record_type == "voucher"
            and r.total_amount > Decimal("0.00")
            and r.total_amount < approval_limit
            and r.vendor_id
        ]
        if vouchers:
            disbursements = vouchers
        else:
            disbursements = [
                r for r in ctx.records
                if r.record_type in ("bank_debit", "ledger_entry")
                and r.total_amount > Decimal("0.00")
                and r.total_amount < approval_limit
                and r.vendor_id
            ]

        # Group by vendor
        vendor_payments: Dict[str, List[any]] = {}
        for d in disbursements:
            vendor_payments.setdefault(d.vendor_id, []).append(d)

        for v_id, p_list in vendor_payments.items():
            if len(p_list) < 2:
                continue

            # Sort by date
            dated_list = [p for p in p_list if p.date]
            dated_list.sort(key=lambda p: p.date)

            # Sliding window search
            for i in range(len(dated_list)):
                window_cluster = [dated_list[i]]
                for j in range(i + 1, len(dated_list)):
                    if abs((dated_list[j].date - dated_list[i].date).days) <= window_days:
                        window_cluster.append(dated_list[j])

                cluster_sum = sum((p.total_amount for p in window_cluster), Decimal("0.00"))
                if len(window_cluster) >= 2 and cluster_sum >= approval_limit:
                    vendor_obj = ctx.db.query(Vendor).filter(Vendor.id == v_id).first()
                    vendor_name = vendor_obj.legal_name if vendor_obj else f"Vendor {v_id[:8]}"

                    amounts_fmt = ", ".join(f"₹{p.total_amount:,.2f}" for p in window_cluster)
                    timespan = (window_cluster[-1].date - window_cluster[0].date).days

                    calc = (
                        f"{len(window_cluster)} payments to '{vendor_name}' totaling ₹{cluster_sum:,.2f} "
                        f"within {timespan} days (Threshold window: {window_days} days), "
                        f"each below approval ceiling limit of ₹{approval_limit:,.2f} ({amounts_fmt})."
                    )

                    evidence = [
                        {"record_id": p.id, "document_id": p.source_document_id, "document_number": p.document_number, "row": p.source_row}
                        for p in window_cluster
                    ]

                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title=f"Potential Split Payments Evading Approval Limit: {vendor_name}",
                        description=f"{len(window_cluster)} payments to '{vendor_name}' total ₹{cluster_sum:,.2f}, circumventing ₹{approval_limit:,.2f} threshold.",
                        reason=f"Splitting contracts or procurement payments to bypass ₹{approval_limit:,.2f} higher-authority sanction is prohibited under KFC rules.",
                        amount_at_risk=cluster_sum,
                        calculation=calc,
                        evidence=evidence,
                        thresholds_used={"window_days": window_days, "approval_limit": float(approval_limit)},
                        inputs_used={
                            "vendor": vendor_name,
                            "cluster_sum": str(cluster_sum),
                            "payment_count": len(window_cluster),
                            "timespan_days": timespan
                        },
                        confidence=95.0
                    ))
                    # Avoid duplicated overlapping clusters
                    break

        return findings
