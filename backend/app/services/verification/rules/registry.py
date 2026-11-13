from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.rules import VerificationRule
from app.services.verification.rules.base import Rule
from app.services.verification.rules.r001_duplicate_payment import RuleDuplicatePayment
from app.services.verification.rules.r002_duplicate_invoice import RuleDuplicateInvoice
from app.services.verification.rules.r003_amount_mismatch import RuleAmountMismatch
from app.services.verification.rules.r004_sanction_vs_payment import RuleSanctionVsPayment
from app.services.verification.rules.r005_bank_vs_bill import RuleBankVsBill
from app.services.verification.rules.r006_tax_validation import RuleTaxValidation
from app.services.verification.rules.r007_arithmetic_validation import RuleArithmeticValidation
from app.services.verification.rules.r008_missing_mandatory_docs import RuleMissingMandatoryDocuments
from app.services.verification.rules.r009_date_logic import RuleDateLogic
from app.services.verification.rules.r010_voucher_sequence import RuleVoucherSequence
from app.services.verification.rules.r011_vendor_concentration import RuleVendorConcentration
from app.services.verification.rules.r012_large_amount import RuleLargeAmount
from app.services.verification.rules.r013_outlier_payments import RuleOutlierPayments
from app.services.verification.rules.r014_split_payments import RuleSplitPayments
from app.services.verification.rules.r015_round_number_benford import RuleRoundNumberAndBenford
from app.services.verification.rules.r016_unusual_timing import RuleUnusualTiming


ALL_RULE_CLASSES: List[type[Rule]] = [
    RuleDuplicatePayment,
    RuleDuplicateInvoice,
    RuleAmountMismatch,
    RuleSanctionVsPayment,
    RuleBankVsBill,
    RuleTaxValidation,
    RuleArithmeticValidation,
    RuleMissingMandatoryDocuments,
    RuleDateLogic,
    RuleVoucherSequence,
    RuleVendorConcentration,
    RuleLargeAmount,
    RuleOutlierPayments,
    RuleSplitPayments,
    RuleRoundNumberAndBenford,
    RuleUnusualTiming,
]


_RULE_INSTANCES: Dict[str, Rule] = {cls.id: cls() for cls in ALL_RULE_CLASSES}


def get_all_rules() -> List[Rule]:
    return list(_RULE_INSTANCES.values())


def get_rule(rule_id: str) -> Optional[Rule]:
    return _RULE_INSTANCES.get(rule_id.upper())


def sync_rules_to_db(db: Session) -> None:
    """Ensures all 16 rules are present in the verification_rules table."""
    import json
    for rule in get_all_rules():
        existing = db.query(VerificationRule).filter(VerificationRule.rule_code == rule.id).first()
        if not existing:
            new_vr = VerificationRule(
                rule_code=rule.id,
                name=rule.name,
                description=rule.description,
                scheme=None,  # All schemes
                severity="medium",
                is_enabled=True,
                parameters_json=json.dumps(rule.default_thresholds)
            )
            db.add(new_vr)
        else:
            if not existing.parameters_json:
                existing.parameters_json = json.dumps(rule.default_thresholds)
    db.flush()
