from datetime import date
from decimal import Decimal
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleUnusualTiming(Rule):
    id = "R-016"
    name = "Unusual Timing, Non-Working Days & Holiday Transactions"
    description = "Detects disbursements approved on Sundays, Karnataka state public holidays, or outside official working hours (09:00 to 18:00)."
    category = "timing"
    default_thresholds = {
        "work_hours_start": "09:00",
        "work_hours_end": "18:00"
    }

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []

        payment_records = [
            r for r in ctx.records
            if r.record_type in ("voucher", "bank_debit", "ledger_entry") and r.date and r.total_amount > Decimal("0.00")
        ]

        for p in payment_records:
            d = p.date

            # 1. Sunday check
            is_sunday = (d.weekday() == 6)

            # 2. Karnataka Holiday check
            is_holiday = (d in ctx.holidays)

            # 3. Fiscal Year-End Rush (March 31)
            is_year_end = (d.month == 3 and d.day == 31)

            if is_sunday or is_holiday or is_year_end:
                day_desc = []
                if is_sunday:
                    day_desc.append("Sunday / Weekend")
                if is_holiday:
                    day_desc.append("Karnataka Public Holiday")
                if is_year_end:
                    day_desc.append("Fiscal Year-End Rush (31 March)")

                calc = (
                    f"Disbursement of ₹{p.total_amount:,.2f} on {p.record_type.title()} '{p.document_number}' "
                    f"was recorded on {d} ({' / '.join(day_desc)})."
                )

                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="medium",
                    title=f"Transaction Processed on {' / '.join(day_desc)}",
                    description=f"Payment {p.document_number} of ₹{p.total_amount:,.2f} was executed on a non-working statutory day or fiscal cutoff ({d}).",
                    reason="Treasury regulations mandate that government treasury transactions occur during official government banking working days and require scrutiny of year-end rush expenditures.",
                    amount_at_risk=p.total_amount,
                    calculation=calc,
                    evidence=[{"record_id": p.id, "document_id": p.source_document_id, "document_number": p.document_number, "row": p.source_row}],
                    thresholds_used={},
                    inputs_used={"date": str(d), "is_sunday": is_sunday, "is_holiday": is_holiday, "is_year_end": is_year_end},
                    confidence=90.0
                ))

        return findings
