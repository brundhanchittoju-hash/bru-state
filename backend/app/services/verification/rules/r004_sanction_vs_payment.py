from decimal import Decimal
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleSanctionVsPayment(Rule):
    id = "R-004"
    name = "Sanction vs Payment & Budget Ceiling"
    description = "Flags when cumulative payments exceed sanctioned amounts, a single payment exceeds sanction limit, or expenditure exceeds estimated project cost beyond tolerance."
    category = "sanction"
    default_thresholds = {"tolerance_pct": 10.0}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        tol_pct = Decimal(str(ctx.thresholds.get("tolerance_pct", self.default_thresholds["tolerance_pct"])))

        sanction_records = [r for r in ctx.records if r.record_type == "sanction"]
        payment_records = [
            r for r in ctx.records
            if r.record_type in ("voucher", "bank_debit", "ledger_entry") and r.total_amount > Decimal("0.00")
        ]

        total_sanction = sum((s.total_amount for s in sanction_records), Decimal("0.00"))
        # If case has estimated_cost or actual_expenditure
        case_est = Decimal(str(ctx.case.estimated_cost)) if ctx.case.estimated_cost else Decimal("0.00")
        case_actual = Decimal(str(ctx.case.actual_expenditure)) if ctx.case.actual_expenditure else Decimal("0.00")

        # Fallback to case estimated cost if no separate sanction record uploaded
        effective_sanction = total_sanction if total_sanction > Decimal("0.00") else case_est

        # Calculate unique voucher disbursement total (deduplicating vouchers vs ledger)
        vouchers = [r for r in payment_records if r.record_type == "voucher"]
        eval_payments = vouchers if vouchers else payment_records
        cumulative_payments = sum((p.total_amount for p in eval_payments), Decimal("0.00"))

        # 1. Cumulative payments exceeding sanction
        if effective_sanction > Decimal("0.00") and cumulative_payments > effective_sanction:
            excess = cumulative_payments - effective_sanction
            excess_pct = (excess / effective_sanction) * Decimal("100.0")
            evidence = [
                {"record_id": p.id, "document_id": p.source_document_id, "document_number": p.document_number, "row": p.source_row}
                for p in eval_payments
            ]
            for s in sanction_records:
                evidence.append({"record_id": s.id, "document_id": s.source_document_id, "document_number": s.document_number})

            calc = (
                f"Cumulative payments ₹{cumulative_payments:,.2f} exceed Sanction ₹{effective_sanction:,.2f} "
                f"by ₹{excess:,.2f} ({excess_pct:.2f}%)"
            )
            findings.append(FindingCandidate(
                rule_id=self.id,
                category=self.category,
                severity="critical",
                title="Cumulative Payments Exceed Sanctioned Ceiling",
                description=f"Total payments of ₹{cumulative_payments:,.2f} exceed the authorized sanction amount of ₹{effective_sanction:,.2f}.",
                reason="Karnataka Financial Code Art. 38 mandates that no expenditure may be incurred in excess of statutory sanction authorization.",
                amount_at_risk=excess,
                calculation=calc,
                evidence=evidence,
                thresholds_used={"tolerance_pct": float(tol_pct)},
                inputs_used={
                    "cumulative_payments": str(cumulative_payments),
                    "sanctioned_amount": str(effective_sanction),
                    "excess": str(excess)
                },
                confidence=100.0
            ))

        # 2. Single payment exceeding sanction
        if effective_sanction > Decimal("0.00"):
            for p in eval_payments:
                if p.total_amount > effective_sanction:
                    calc = f"Single payment of ₹{p.total_amount:,.2f} exceeds total sanction amount of ₹{effective_sanction:,.2f}"
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="critical",
                        title="Single Payment Exceeds Total Project Sanction",
                        description=f"A single disbursement of ₹{p.total_amount:,.2f} (Doc: {p.document_number}) exceeds total sanction ₹{effective_sanction:,.2f}.",
                        reason="Individual voucher disbursement exceeds the total project sanction authorized for this scheme.",
                        amount_at_risk=p.total_amount - effective_sanction,
                        calculation=calc,
                        evidence=[{"record_id": p.id, "document_id": p.source_document_id, "document_number": p.document_number}],
                        thresholds_used={"tolerance_pct": float(tol_pct)},
                        inputs_used={"payment_amount": str(p.total_amount), "sanction": str(effective_sanction)},
                        confidence=100.0
                    ))

        # 3. Case actual expenditure exceeding estimated cost beyond tolerance
        if case_est > Decimal("0.00") and case_actual > Decimal("0.00"):
            allowed_max = case_est * (Decimal("1.0") + (tol_pct / Decimal("100.0")))
            if case_actual > allowed_max:
                cost_overrun = case_actual - case_est
                cost_pct = (cost_overrun / case_est) * Decimal("100.0")
                calc = (
                    f"Actual expenditure ₹{case_actual:,.2f} exceeds estimate ₹{case_est:,.2f} by "
                    f"₹{cost_overrun:,.2f} ({cost_pct:.2f}%), allowed tolerance: {tol_pct:.1f}%"
                )
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="high",
                    title="Actual Expenditure Exceeds Estimated Budget Beyond Tolerance",
                    description=f"Case actual expenditure ₹{case_actual:,.2f} exceeds approved estimate ₹{case_est:,.2f} by {cost_pct:.2f}%.",
                    reason=f"Expenditure overrun exceeds the permissible tolerance threshold of {tol_pct:.1f}%.",
                    amount_at_risk=cost_overrun,
                    calculation=calc,
                    evidence=[],
                    thresholds_used={"tolerance_pct": float(tol_pct)},
                    inputs_used={"actual": str(case_actual), "estimate": str(case_est), "overrun_pct": float(cost_pct)},
                    confidence=95.0
                ))

        return findings
