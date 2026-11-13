from decimal import Decimal
import json
from typing import List
from app.services.extraction.parser_utils import parse_indian_amount, words_to_indian_amount
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleArithmeticValidation(Rule):
    id = "R-007"
    name = "Document Arithmetic & Words-to-Numbers Consistency"
    description = "Verifies internal arithmetic consistency: subtotal + tax equals total amount, line item additions, and numerical amount matching amount written in words."
    category = "arithmetic"
    default_thresholds = {"tolerance": 1.0}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        tolerance = Decimal(str(ctx.thresholds.get("tolerance", self.default_thresholds["tolerance"])))

        bill_records = [r for r in ctx.records if r.record_type == "bill"]

        for b in bill_records:
            meta = {}
            if b.raw_data_json:
                try:
                    meta = json.loads(b.raw_data_json)
                except Exception:
                    meta = {}

            base_amt = b.base_amount
            tax_amt = b.tax_amount
            total_amt = b.total_amount

            # 1. Base + Tax == Total Check
            if base_amt is not None and tax_amt is not None and total_amt > Decimal("0.00"):
                expected_total = base_amt + tax_amt
                diff = abs(total_amt - expected_total)
                if diff > tolerance:
                    calc = (
                        f"Subtotal ₹{base_amt:,.2f} + Tax ₹{tax_amt:,.2f} = ₹{expected_total:,.2f}, "
                        f"which does not match recorded Total ₹{total_amt:,.2f} (Difference: ₹{diff:,.2f}, tolerance: ₹{tolerance:,.2f})"
                    )
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="medium",
                        title="Subtotal and Tax Do Not Equal Total Amount",
                        description=f"Arithmetic discrepancy of ₹{diff:,.2f} detected on bill {b.document_number}.",
                        reason="Fundamental bookkeeping integrity requires that taxable subtotal plus tax equals the gross invoice total.",
                        amount_at_risk=diff,
                        calculation=calc,
                        evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number}],
                        thresholds_used={"tolerance": float(tolerance)},
                        inputs_used={"base": str(base_amt), "tax": str(tax_amt), "total": str(total_amt), "diff": str(diff)},
                        confidence=100.0
                    ))

            # 2. Line Items vs Subtotal Check (if present in metadata or raw text)
            line_sum_str = meta.get("line_items_total")
            if line_sum_str:
                parsed_line_amt, _ = parse_indian_amount(line_sum_str)
                line_sum = parsed_line_amt or Decimal("0.00")
                eval_subtotal = base_amt if base_amt and base_amt > 0 else total_amt
                if line_sum > Decimal("0.00") and abs(line_sum - eval_subtotal) > tolerance:
                    diff = abs(line_sum - eval_subtotal)
                    calc = f"Sum of line items ₹{line_sum:,.2f} does not equal subtotal ₹{eval_subtotal:,.2f} (Difference: ₹{diff:,.2f})"
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="medium",
                        title="Line Items Sum Mismatch",
                        description=f"Individual line item additions on bill {b.document_number} differ from subtotal by ₹{diff:,.2f}.",
                        reason="Invoice arithmetic validation failed on itemized schedule additions.",
                        amount_at_risk=diff,
                        calculation=calc,
                        evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number}],
                        thresholds_used={"tolerance": float(tolerance)},
                        inputs_used={"line_sum": str(line_sum), "subtotal": str(eval_subtotal), "diff": str(diff)},
                        confidence=95.0
                    ))

            # 3. Words to Numbers Consistency Check
            words_str = meta.get("amount_in_words")
            if words_str and total_amt > Decimal("0.00"):
                parsed_words_val = words_to_indian_amount(words_str)
                if parsed_words_val is not None:
                    parsed_words_dec = Decimal(str(parsed_words_val))
                    if abs(parsed_words_dec - total_amt) > tolerance:
                        diff = abs(parsed_words_dec - total_amt)
                        calc = (
                            f"Amount written in words ('{words_str}' -> ₹{parsed_words_dec:,.2f}) "
                            f"does not match numeral amount ₹{total_amt:,.2f} (Difference: ₹{diff:,.2f})"
                        )
                        findings.append(FindingCandidate(
                            rule_id=self.id,
                            category=self.category,
                            severity="medium",
                            title="Discrepancy Between Words and Numerical Amount",
                            description=f"Amount in words indicates ₹{parsed_words_dec:,.2f} while numerical figure reads ₹{total_amt:,.2f}.",
                            reason="Section 18 of the Negotiable Instruments Act and state audit rules require words and figures to correspond exactly.",
                            amount_at_risk=diff,
                            calculation=calc,
                            evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number}],
                            thresholds_used={"tolerance": float(tolerance)},
                            inputs_used={"words": words_str, "parsed_words": str(parsed_words_dec), "numerical": str(total_amt)},
                            confidence=95.0
                        ))

        return findings
