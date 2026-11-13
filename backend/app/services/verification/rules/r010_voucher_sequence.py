from decimal import Decimal
import re
from typing import Dict, List, Tuple
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


def split_voucher_prefix_num(v_str: str) -> Tuple[str, int]:
    """Splits 'V-101' into ('V-', 101) or 'VR/2024/005' into ('VR/2024/', 5)."""
    if not v_str:
        return "", 0
    match = re.search(r"^(.*?)(\d+)$", v_str.strip())
    if match:
        prefix = match.group(1)
        num = int(match.group(2))
        return prefix, num
    return "", 0


class RuleVoucherSequence(Rule):
    id = "R-010"
    name = "Voucher Sequential Integrity & Gap Detection"
    description = "Detects sequence breaks, missing voucher numbers, and numbering duplicates within voucher series."
    category = "compliance"
    default_thresholds = {}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        vouchers = [
            r for r in ctx.records
            if r.record_type in ("voucher", "ledger_entry") and r.document_number
        ]

        # Group by prefix
        series_map: Dict[str, List[Tuple[int, any]]] = {}
        dup_check: Dict[str, List[any]] = {}

        for v in vouchers:
            v_num = v.document_number.strip()
            dup_check.setdefault(v_num.upper(), []).append(v)

            prefix, num = split_voucher_prefix_num(v_num)
            if prefix and num > 0:
                series_map.setdefault(prefix, []).append((num, v))

        # 1. Duplicate Voucher Numbers
        for v_num, recs in dup_check.items():
            if len(recs) > 1:
                evidence = [
                    {"record_id": r.id, "document_id": r.source_document_id, "document_number": r.document_number, "row": r.source_row}
                    for r in recs
                ]
                calc = f"Voucher number '{v_num}' appears on {len(recs)} distinct records."
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="high",
                    title=f"Duplicate Voucher Number: {v_num}",
                    description=f"Voucher identifier '{v_num}' is duplicated across {len(recs)} transactions.",
                    reason="Voucher registers require strictly unique sequential numbering to prevent double entry.",
                    amount_at_risk=sum((r.total_amount for r in recs), Decimal("0.00")),
                    calculation=calc,
                    evidence=evidence,
                    inputs_used={"voucher_number": v_num, "count": len(recs)},
                    confidence=100.0
                ))

        # 2. Sequence Gaps within series
        for prefix, items in series_map.items():
            if len(items) < 2:
                continue

            # Sort by numeric sequence
            items.sort(key=lambda x: x[0])
            nums = [x[0] for x in items]
            rec_map = {x[0]: x[1] for x in items}

            min_n = min(nums)
            max_n = max(nums)

            # Only evaluate reasonable contiguous ranges (< 100 gaps) to avoid false positives across FY series
            if max_n - min_n < 200:
                missing = []
                for n in range(min_n, max_n + 1):
                    if n not in rec_map:
                        missing.append(n)

                if missing:
                    missing_labels = [f"{prefix}{m}" for m in missing[:10]]
                    calc = f"Sequence break in voucher series '{prefix}': {len(missing)} missing numbers detected (e.g. {', '.join(missing_labels)})."
                    evidence = [
                        {"record_id": items[0][1].id, "document_id": items[0][1].source_document_id, "document_number": items[0][1].document_number},
                        {"record_id": items[-1][1].id, "document_id": items[-1][1].source_document_id, "document_number": items[-1][1].document_number}
                    ]
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="medium",
                        title=f"Voucher Sequence Break in Series '{prefix}'",
                        description=f"{len(missing)} voucher numbers are missing between {prefix}{min_n} and {prefix}{max_n}.",
                        reason="Karnataka Panchayati Raj Accounting Rules mandate unbroken sequential voucher continuity.",
                        amount_at_risk=Decimal("0.00"),
                        calculation=calc,
                        evidence=evidence,
                        inputs_used={"prefix": prefix, "missing_count": len(missing), "missing_samples": missing_labels},
                        confidence=90.0
                    ))

            # 3. Chronological Date Inversion in sequential numbering
            for i in range(len(items) - 1):
                n1, r1 = items[i]
                n2, r2 = items[i + 1]
                if r1.date and r2.date and r1.date > r2.date:
                    days_diff = (r1.date - r2.date).days
                    calc = (
                        f"Voucher {r1.document_number} (dated {r1.date}) precedes "
                        f"higher-numbered voucher {r2.document_number} (dated {r2.date}) by {days_diff} days."
                    )
                    evidence = [
                        {"record_id": r1.id, "document_id": r1.source_document_id, "document_number": r1.document_number, "row": r1.source_row},
                        {"record_id": r2.id, "document_id": r2.source_document_id, "document_number": r2.document_number, "row": r2.source_row}
                    ]
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title=f"Chronological Date Inversion: {r1.document_number} vs {r2.document_number}",
                        description=f"Voucher {r1.document_number} dated {r1.date} has a later date than successor voucher {r2.document_number} dated {r2.date}.",
                        reason="Vouchers must be recorded in strict ascending chronological order. Date reversals indicate backdated vouchers.",
                        amount_at_risk=r2.total_amount,
                        calculation=calc,
                        evidence=evidence,
                        inputs_used={"v1": r1.document_number, "d1": str(r1.date), "v2": r2.document_number, "d2": str(r2.date)},
                        confidence=95.0
                    ))

        return findings
