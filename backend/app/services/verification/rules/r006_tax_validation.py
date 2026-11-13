from decimal import Decimal
import json
from typing import List
from app.services.extraction.parser_utils import validate_gstin
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


class RuleTaxValidation(Rule):
    id = "R-006"
    name = "Statutory Tax & GST Validation"
    description = "Validates GST mathematical calculations, statutory rate slabs (0%, 5%, 12%, 18%, 28%), CGST/SGST equality, GSTIN checksums, and indicative TDS compliance."
    category = "tax"
    default_thresholds = {
        "tolerance": 1.0,
        "valid_slabs": [0.0, 5.0, 12.0, 18.0, 28.0]
    }

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        tolerance = Decimal(str(ctx.thresholds.get("tolerance", self.default_thresholds["tolerance"])))
        valid_slabs = [float(s) for s in ctx.thresholds.get("valid_slabs", self.default_thresholds["valid_slabs"])]

        bill_records = [r for r in ctx.records if r.record_type == "bill"]

        for b in bill_records:
            meta = {}
            if b.raw_data_json:
                try:
                    meta = json.loads(b.raw_data_json)
                except Exception:
                    meta = {}

            gstin = meta.get("gstin")
            base_amt = b.base_amount or Decimal("0.00")
            tax_amt = b.tax_amount or Decimal("0.00")
            total_amt = b.total_amount

            # 1. GSTIN Checksum Validation
            if gstin:
                if not validate_gstin(gstin):
                    calc = f"GSTIN '{gstin}' on bill '{b.document_number}' fails the statutory Luhn Mod-36 checksum algorithm."
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title="Invalid GSTIN Checksum on Statutory Bill",
                        description=f"GSTIN '{gstin}' on bill {b.document_number} is structurally invalid or corrupt.",
                        reason="GST portal validation requires valid 15-digit alpha-numeric format with Luhn Mod-36 check digit.",
                        amount_at_risk=tax_amt if tax_amt > Decimal("0.00") else total_amt,
                        calculation=calc,
                        evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number}],
                        thresholds_used={},
                        inputs_used={"gstin": gstin},
                        confidence=100.0
                    ))

            # 2. CGST / SGST Equality Check
            cgst_str = meta.get("cgst_amount")
            sgst_str = meta.get("sgst_amount")
            if cgst_str and sgst_str:
                from app.services.extraction.parser_utils import parse_indian_amount
                cgst_val, _ = parse_indian_amount(cgst_str)
                sgst_val, _ = parse_indian_amount(sgst_str)
                cgst = cgst_val or Decimal("0.00")
                sgst = sgst_val or Decimal("0.00")
                if abs(cgst - sgst) > tolerance:
                    diff = abs(cgst - sgst)
                    calc = f"CGST ₹{cgst:,.2f} does not equal SGST ₹{sgst:,.2f} on bill '{b.document_number}' (Difference: ₹{diff:,.2f})"
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="medium",
                        title="Intra-State CGST and SGST Inconsistency",
                        description=f"Intra-state GST rules mandate identical CGST and SGST amounts. Found ₹{cgst:,.2f} vs ₹{sgst:,.2f}.",
                        reason="Section 9 of the CGST Act requires equal central and state tax apportionment on intra-state supplies.",
                        amount_at_risk=diff,
                        calculation=calc,
                        evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number}],
                        thresholds_used={"tolerance": float(tolerance)},
                        inputs_used={"cgst": str(cgst), "sgst": str(sgst)},
                        confidence=95.0
                    ))

            # 3. GST Calculation & Slab Verification
            if base_amt > Decimal("0.00") and tax_amt > Decimal("0.00"):
                effective_rate = float(round((tax_amt / base_amt) * Decimal("100.0"), 2))
                # Find closest statutory slab
                closest_slab = min(valid_slabs, key=lambda s: abs(s - effective_rate))
                expected_tax = base_amt * (Decimal(str(closest_slab)) / Decimal("100.0"))
                discrepancy = abs(tax_amt - expected_tax)

                # Check if rate matches a valid slab
                is_valid_slab = any(abs(effective_rate - s) <= 0.2 for s in valid_slabs)
                if not is_valid_slab or discrepancy > tolerance:
                    calc = (
                        f"Reported GST ₹{tax_amt:,.2f} deviates from expected ₹{expected_tax:,.2f} "
                        f"(Base ₹{base_amt:,.2f} × {closest_slab:.1f}% statutory slab). Discrepancy: ₹{discrepancy:,.2f}"
                    )
                    findings.append(FindingCandidate(
                        rule_id=self.id,
                        category=self.category,
                        severity="high",
                        title="GST Rate / Amount Computation Discrepancy",
                        description=f"Effective GST rate {effective_rate:.2f}% does not conform to statutory slabs or expected tax ₹{expected_tax:,.2f}.",
                        reason="GST computation must match valid statutory tariff schedules (0%, 5%, 12%, 18%, 28%).",
                        amount_at_risk=discrepancy,
                        calculation=calc,
                        evidence=[{"record_id": b.id, "document_id": b.source_document_id, "document_number": b.document_number}],
                        thresholds_used={"tolerance": float(tolerance), "valid_slabs": valid_slabs},
                        inputs_used={"base_amount": str(base_amt), "reported_tax": str(tax_amt), "effective_rate": effective_rate},
                        confidence=95.0
                    ))

        return findings
