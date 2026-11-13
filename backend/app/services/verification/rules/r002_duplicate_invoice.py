import re
from typing import List
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


def normalize_invoice_number(inv: str) -> str:
    if not inv:
        return ""
    # strip whitespace, hyphens, underscores, slashes, leading zeros
    cleaned = re.sub(r"[\s\-_/]", "", inv).lower()
    # strip leading zeros from numeric components
    cleaned = re.sub(r"^0+", "", cleaned)
    return cleaned


class RuleDuplicateInvoice(Rule):
    id = "R-002"
    name = "Duplicate Invoice Number"
    description = "Detects duplicate invoice numbers from the same vendor across exact matches and normalized variants (spaces, hyphens, slashes, leading zeros)."
    category = "duplicate"
    default_thresholds = {}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        bills = [r for r in ctx.records if r.record_type == "bill" and r.document_number]

        for i in range(len(bills)):
            for j in range(i + 1, len(bills)):
                b1 = bills[i]
                b2 = bills[j]

                # Same vendor check
                if b1.vendor_id and b2.vendor_id and b1.vendor_id == b2.vendor_id:
                    n1 = normalize_invoice_number(b1.document_number)
                    n2 = normalize_invoice_number(b2.document_number)

                    if n1 and n2 and (n1 == n2 or b1.document_number.strip().lower() == b2.document_number.strip().lower()):
                        evidence = [
                            {"record_id": b1.id, "document_id": b1.source_document_id, "document_number": b1.document_number},
                            {"record_id": b2.id, "document_id": b2.source_document_id, "document_number": b2.document_number}
                        ]
                        calc = f"Invoice '{b1.document_number}' matches invoice '{b2.document_number}' (Normalized form: '{n1}') for the same vendor."
                        findings.append(FindingCandidate(
                            rule_id=self.id,
                            category=self.category,
                            severity="high",
                            title="Duplicate Invoice Number Detected",
                            description=f"Duplicate invoice identifier '{b1.document_number}' and '{b2.document_number}' submitted by the same vendor.",
                            reason="Karnataka Financial Code prohibits resubmission of duplicate invoice numbers for identical statutory claims.",
                            amount_at_risk=b2.total_amount,
                            calculation=calc,
                            evidence=evidence,
                            thresholds_used={},
                            inputs_used={"invoice_1": b1.document_number, "invoice_2": b2.document_number, "normalized": n1},
                            confidence=100.0
                        ))

        return findings
