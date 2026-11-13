from decimal import Decimal
from typing import List
from app.models.system import MandatoryDocumentChecklist
from app.services.verification.rules.base import FindingCandidate, Rule, VerificationContext


DEFAULT_SCHEME_CHECKLISTS = {
    "MGNREGA": ["Bill", "Voucher", "Sanction Order", "Work Order", "Measurement Book", "Completion Certificate"],
    "PMAY-G": ["Bill", "Voucher", "Sanction Order", "Completion Certificate"],
    "15th Finance Commission Grants": ["Voucher", "Sanction Order", "Utilization Certificate"],
    "Jal Jeevan Mission": ["Bill", "Voucher", "Sanction Order", "Work Order", "Measurement Book", "Completion Certificate"],
    "Swachh Bharat Mission (Gramin)": ["Bill", "Voucher", "Sanction Order", "Utilization Certificate"],
    "Default": ["Bill", "Voucher", "Sanction Order"]
}


class RuleMissingMandatoryDocuments(Rule):
    id = "R-008"
    name = "Missing Mandatory Statutory Documents"
    description = "Checks that all mandatory compliance documents mandated for the scheme and audit type (Sanction, Bill, Voucher, Work Order, Measurement Book, Completion/Utilization Certificate) are present."
    category = "compliance"
    default_thresholds = {}

    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        findings = []
        scheme = ctx.case.scheme_name or "Default"

        # 1. Fetch configured checklist from DB or default
        checklists = ctx.db.query(MandatoryDocumentChecklist).filter(
            MandatoryDocumentChecklist.scheme_name == scheme,
            MandatoryDocumentChecklist.is_mandatory == True,
            MandatoryDocumentChecklist.deleted_at.is_(None)
        ).all()

        required_doc_types = [c.document_type for c in checklists]
        if not required_doc_types:
            # Fallback to default scheme list
            required_doc_types = DEFAULT_SCHEME_CHECKLISTS.get(scheme, DEFAULT_SCHEME_CHECKLISTS["Default"])

        # 2. Collect existing document types in the case
        present_types = set()
        for doc in ctx.documents:
            if doc.document_type:
                present_types.add(doc.document_type.strip().lower())

        # Also check FinancialRecord types
        for r in ctx.records:
            present_types.add(r.record_type.replace("_", " ").lower())

        # 3. Check for missing document types
        for req in required_doc_types:
            req_lower = req.strip().lower()
            # Match variations
            matched = any(
                req_lower in p or p in req_lower
                for p in present_types
            )
            if not matched:
                calc = f"Scheme '{scheme}' mandates '{req}'; 0 documents of type '{req}' uploaded in case {ctx.case.case_number}."
                findings.append(FindingCandidate(
                    rule_id=self.id,
                    category=self.category,
                    severity="high",
                    title=f"Missing Mandatory Document: {req}",
                    description=f"Statutory document '{req}' required under scheme '{scheme}' is missing from the audit case file.",
                    reason=f"Government financial rules require a verified {req} prior to passing payments or closing audit paras.",
                    amount_at_risk=Decimal(str(ctx.case.actual_expenditure or ctx.case.estimated_cost or 0.0)),
                    calculation=calc,
                    evidence=[],
                    thresholds_used={"required_type": req, "scheme": scheme},
                    inputs_used={"scheme": scheme, "missing_document": req},
                    confidence=100.0
                ))

        return findings
