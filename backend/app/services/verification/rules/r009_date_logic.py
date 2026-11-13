from datetime import date
from decimal import Decimal
from typing import List, Tuple
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


def parse_fy_bounds(fy_str: str) -> Tuple[date, date]:
    """Parse FY string like '2024-2025' or '2024-25' into (start_date, end_date)

    Indian Financial Year runs April 1 to March 31.
    """
    try:
        parts = fy_str.replace("FY", "").strip().split("-")
        start_year = int(parts[0].strip())
        end_year = start_year + 1
        return date(start_year, 4, 1), date(end_year, 3, 31)
    except Exception:
        # Fallback to current calendar span
        today = date.today()
        return date(today.year - 1, 4, 1), date(today.year + 1, 3, 31)


class RuleDateLogic(Rule):
    id = "R-009"
    name = "Chronological Sequence & Financial Year Date Logic"
    description = "Enforces statutory chronological ordering (Sanction -> Work Order -> Bill -> Voucher -> Payment) and checks for future dates or dates outside the case financial year."
    category = "dates"
    default_thresholds = {}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        today = date.today()
        fy_start, fy_end = parse_fy_bounds(ctx.case.financial_year)

        bills = [r for r in ctx.records if r.record_type == "bill" and r.date]
        vouchers = [r for r in ctx.records if r.record_type == "voucher" and r.date]
        sanctions = [r for r in ctx.records if r.record_type == "sanction" and r.date]
        work_orders = [r for r in ctx.records if r.record_type == "work_order" and r.date]
        completions = [r for r in ctx.records if r.record_type == "completion_certificate" and r.date]

        # 1. Future Dates & Outside Financial Year check
        for r in ctx.records:
            if not r.date:
                continue

            # Future date check
            if r.date > today:
                calc = f"Record '{r.document_number}' has date {r.date}, which is in the future relative to current date {today}."
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="critical",
                    title="Future Dated Document / Transaction",
                    description=f"Transaction document {r.document_number} bears an impossible future date ({r.date}).",
                    reason="Statutory accounting rules prohibit backdating or future-dating financial records.",
                    amount_at_risk=r.total_amount,
                    calculation=calc,
                    evidence=[{"record_id": r.id, "document_id": r.source_document_id, "document_number": r.document_number}],
                    confidence=100.0
                ))

            # Outside FY check
            if r.date < fy_start or r.date > fy_end:
                calc = f"Document '{r.document_number}' dated {r.date} falls outside Case Financial Year {ctx.case.financial_year} ({fy_start} to {fy_end})."
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="medium",
                    title="Transaction Date Outside Case Financial Year",
                    description=f"Record {r.document_number} dated {r.date} falls outside the assigned audit period {ctx.case.financial_year}.",
                    reason="Karnataka State Audit Department reviews require financial records to strictly coincide with the audited financial year.",
                    amount_at_risk=r.total_amount,
                    calculation=calc,
                    evidence=[{"record_id": r.id, "document_id": r.source_document_id, "document_number": r.document_number}],
                    inputs_used={"date": str(r.date), "fy": ctx.case.financial_year},
                    confidence=95.0
                ))

        # 2. Chronological sequence: Payment Voucher before Sanction Order
        for v in vouchers:
            for s in sanctions:
                if v.date < s.date:
                    days_prior = (s.date - v.date).days
                    calc = f"Payment Voucher '{v.document_number}' dated {v.date} precedes Sanction Order '{s.document_number}' dated {s.date} by {days_prior} days."
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title="Payment Disbursed Before Sanction Order Date",
                        description=f"Payment voucher {v.document_number} was issued {days_prior} days before sanction authorization was approved.",
                        reason="KFC Article 35: No payment may be released prior to formal administrative and financial sanction approval.",
                        amount_at_risk=v.total_amount,
                        calculation=calc,
                        evidence=[
                            {"record_id": v.id, "document_id": v.source_document_id, "document_number": v.document_number},
                            {"record_id": s.id, "document_id": s.source_document_id, "document_number": s.document_number}
                        ],
                        inputs_used={"voucher_date": str(v.date), "sanction_date": str(s.date), "days_prior": days_prior},
                        confidence=100.0
                    ))

        # 3. Chronological sequence: Bill before Work Order
        wo_bill_pairs = set()
        for link in ctx.links:
            if link.link_type == "work_order_to_bill":
                wo_bill_pairs.add((link.source_record_id, link.target_record_id))

        for b in bills:
            for wo in work_orders:
                is_related = (wo.id, b.id) in wo_bill_pairs or (wo.vendor_id and b.vendor_id and wo.vendor_id == b.vendor_id)
                if not is_related and (len(work_orders) > 1 or len(bills) > 1):
                    continue
                if b.date < wo.date:
                    days_prior = (wo.date - b.date).days
                    calc = f"Vendor Bill '{b.document_number}' dated {b.date} precedes Work Order '{wo.document_number}' dated {wo.date} by {days_prior} days."
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title="Vendor Bill Incurred Prior to Work Order Issuance",
                        description=f"Vendor invoice {b.document_number} is dated {days_prior} days prior to contractual work order issuance.",
                        reason="Procurement guidelines require work orders to precede contractor execution and billing.",
                        amount_at_risk=b.total_amount,
                        calculation=calc,
                        evidence=[
                            {"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number},
                            {"record_id": wo.id, "document_id": wo.source_document_id, "document_number": wo.document_number}
                        ],
                        inputs_used={"bill_date": str(b.date), "work_order_date": str(wo.date), "days_prior": days_prior},
                        confidence=100.0
                    ))

        # 4. Chronological sequence: Completion Certificate before Work Order
        for cc in completions:
            for wo in work_orders:
                if cc.date < wo.date:
                    calc = f"Completion Certificate '{cc.document_number}' dated {cc.date} precedes Work Order '{wo.document_number}' dated {wo.date}."
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title="Completion Certificate Precedes Work Order",
                        description=f"Project completion certification {cc.document_number} is dated prior to work order issuance.",
                        reason="Work completion cannot chronologically precede formal contractual commencement.",
                        amount_at_risk=wo.total_amount,
                        calculation=calc,
                        evidence=[
                            {"record_id": cc.id, "document_id": cc.source_document_id, "document_number": cc.document_number},
                            {"record_id": wo.id, "document_id": wo.source_document_id, "document_number": wo.document_number}
                        ],
                        confidence=100.0
                    ))

        return findings
