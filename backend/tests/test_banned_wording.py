import pytest
from app.services.verification.rules.registry import get_all_rules
from app.core.database import SessionLocal
from app.models.finding import Finding
from app.models.rules import VerificationRule

BANNED_WORDS = [
    "fraud",
    "fraudulent",
    "theft",
    "embezzlement",
    "scam",
    "corrupt",
    "misappropriation"
]


def test_no_banned_words_in_rule_templates():
    """Verifies that all 16 statutory rule templates, names, descriptions,

    and generated findings contain ZERO banned subjective accusation terms.
    The system strictly assists auditors with objective phrases like 'flagged for review'
    or 'recommended for review' without making legal culpability determinations.
    """
    rules = get_all_rules()
    violations = []

    for rule in rules:
        text_corpus = f"{rule.id} {rule.name} {rule.description} {rule.category}".lower()
        for banned in BANNED_WORDS:
            if banned in text_corpus:
                violations.append(f"Rule {rule.id} static definition contains banned word '{banned}'")

    assert not violations, f"Banned words detected in rule templates: {violations}"


def test_no_banned_words_in_active_findings_database():
    """Scans all seeded finding titles, descriptions, and statutory reasons in the database

    to ensure 0 occurrences of banned subjective wording.
    """
    db = SessionLocal()
    try:
        findings = db.query(Finding).all()
        violations = []

        for f in findings:
            finding_text = f"{f.title} {f.description} {f.reason or ''} {f.calculation or ''}".lower()
            for banned in BANNED_WORDS:
                if banned in finding_text:
                    violations.append(f"Finding {f.finding_number} ({f.rule_id}) contains banned word '{banned}': {f.title}")

        assert not violations, f"Banned words detected in database findings: {violations}"
    finally:
        db.close()
