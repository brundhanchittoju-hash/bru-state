import re
from typing import Dict, List, Tuple, Any, Optional

# ==============================================================================
# 13 Standard Document Classes & Bilingual Keyword Rules
# ==============================================================================

DOCUMENT_CLASSES = [
    "Bill",
    "Voucher",
    "Tender",
    "Bank Statement",
    "Ledger",
    "Sanction Order",
    "Work Order",
    "Measurement Book",
    "Cash Book",
    "Completion Certificate",
    "Utilization Certificate",
    "Supporting Document",
    "Unknown",
]

# Weighted keywords and phrases: tuple of (pattern_or_phrase, weight)
CLASS_RULES: Dict[str, List[Tuple[str, float]]] = {
    "Bill": [
        (r"\btax\s+invoice\b", 4.0),
        (r"\bbill\s+of\s+supply\b", 3.5),
        (r"\binvoice\s+no\b", 3.0),
        (r"\bbill\s+no\b", 3.0),
        (r"\bgstin\b", 2.0),
        (r"\bvendor\b", 1.5),
        (r"\bhsn\s*[\/\-]?\s*sac\b", 2.5),
        (r"\bcommercial\s+tax\b", 2.0),
        (r"ಬಿಲ್", 3.5),
        (r"ತೆರಿಗೆ\s+ಇನ್‌ವಾಯ್ಸ್", 4.0),
        (r"ಇನ್ವಾಯ್ಸ್", 3.0),
    ],
    "Voucher": [
        (r"\bpayment\s+voucher\b", 4.5),
        (r"\bdebit\s+voucher\b", 4.0),
        (r"\bvoucher\s+no\b", 3.5),
        (r"\bvr\s+no\b", 3.0),
        (r"\bhead\s+of\s+account\b", 2.5),
        (r"\bpassed\s+for\s+payment\b", 3.0),
        (r"\bcheque\s+no\b", 2.0),
        (r"\brs\.\s*in\s+words\b", 1.5),
        (r"ಪಾವತಿ\s+ಚೀಟಿ", 4.5),
        (r"ರಶೀದಿ", 3.5),
        (r"ಖರ್ಚು\s+ಚೀಟಿ", 4.0),
    ],
    "Work Order": [
        (r"\bwork\s+order\b", 4.5),
        (r"\bjob\s+order\b", 4.0),
        (r"\baward\s+of\s+work\b", 4.0),
        (r"\bcontract\s+agreement\b", 3.0),
        (r"\bstipulated\s+date\s+of\s+commencement\b", 3.0),
        (r"\bstipulated\s+date\s+of\s+completion\b", 3.0),
        (r"\btender\s+premium\b", 2.0),
        (r"ಕಾರ್ಯಾದೇಶ", 4.5),
        (r"ಕೆಲಸದ\s+ಆದೇಶ", 4.0),
    ],
    "Sanction Order": [
        (r"\badministrative\s+sanction\b", 4.5),
        (r"\btechnical\s+sanction\b", 4.5),
        (r"\bsanction\s+order\b", 4.0),
        (r"\bgrant\s+in\s+aid\b", 3.0),
        (r"\bgovernment\s+order\b", 3.0),
        (r"\bproceeding\s+of\b", 2.5),
        (r"\bsanctioned\s+estimate\b", 3.0),
        (r"ಮಂಜೂರಾತಿ\s+ಆದೇಶ", 4.5),
        (r"ಆಡಳಿತಾತ್ಮಕ\s+ಮಂಜೂರಾತಿ", 4.5),
        (r"ತಾಂತ್ರಿಕ\s+ಮಂಜೂರಾತಿ", 4.5),
    ],
    "Tender": [
        (r"\bnotice\s+inviting\s+tender\b", 4.5),
        (r"\bshort\s+term\s+tender\b", 4.0),
        (r"\be\-procurement\b", 3.5),
        (r"\bearnest\s+money\s+deposit\b", 3.5),
        (r"\bemd\b", 2.0),
        (r"\btender\s+document\b", 3.0),
        (r"\btender\s+notification\b", 3.5),
        (r"ಟೆಂಡರ್\s+ಪ್ರಕಟಣೆ", 4.5),
        (r"ಟೆಂಡರ್", 3.5),
    ],
    "Measurement Book": [
        (r"\bmeasurement\s+book\b", 5.0),
        (r"\bm[\-\s]?book\b", 4.5),
        (r"\bmb\s+no\b", 4.0),
        (r"\brunning\s+account\s+bill\b", 3.5),
        (r"\bra\s+bill\b", 3.0),
        (r"\bmeasurements\s+recorded\b", 3.5),
        (r"\bchainage\b", 2.5),
        (r"\bitems\s+of\s+work\b", 2.0),
        (r"ಅಳತೆ\s+ಪುಸ್ತಕ", 5.0),
    ],
    "Completion Certificate": [
        (r"\bwork\s+completion\s+certificate\b", 5.0),
        (r"\bcompletion\s+certificate\b", 4.5),
        (r"\bsatisfactorily\s+completed\b", 3.5),
        (r"\bactual\s+date\s+of\s+completion\b", 3.5),
        (r"\bfinal\s+bill\b", 2.5),
        (r"ಕಾರ್ಯ\s+ಪೂರ್ಣಗೊಂಡ\s+ಪ್ರಮಾಣಪತ್ರ", 5.0),
        (r"ಪೂರ್ಣಗೊಂಡ\s+ಪ್ರಮಾಣಪತ್ರ", 4.5),
    ],
    "Utilization Certificate": [
        (r"\butilization\s+certificate\b", 5.0),
        (r"\bform\s+gfr\s*12[\-A-Z]*\b", 4.5),
        (r"\bcertified\s+that\s+out\s+of\s+rs\b", 4.0),
        (r"\bgrants\-in\-aid\b", 3.0),
        (r"\butilized\s+for\s+the\s+purpose\b", 4.0),
        (r"\bbalance\s+remaining\s+unutilized\b", 3.5),
        (r"ಬಳಕೆ\s+ಪ್ರಮಾಣಪತ್ರ", 5.0),
    ],
    "Cash Book": [
        (r"\bcash\s+book\b", 4.5),
        (r"\bpetty\s+cash\b", 4.0),
        (r"\bopening\s+cash\s+balance\b", 3.5),
        (r"\bclosing\s+cash\s+balance\b", 3.5),
        (r"\breceipts\s+and\s+payments\b", 2.5),
        (r"ನಗದು\s+ಪುಸ್ತಕ", 4.5),
    ],
    "Ledger": [
        (r"\bgeneral\s+ledger\b", 4.5),
        (r"\bscheme\s+ledger\b", 4.0),
        (r"\bledger\s+account\b", 4.0),
        (r"\bjournal\s+folio\b", 3.0),
        (r"\bhead\s+wise\s+ledger\b", 3.5),
        (r"ಖಾತೆ\s+ಪುಸ್ತಕ", 4.5),
        (r"ಲೆಡ್ಜರ್", 3.5),
    ],
    "Bank Statement": [
        (r"\bbank\s+statement\b", 4.5),
        (r"\baccount\s+statement\b", 4.0),
        (r"\btransaction\s+history\b", 3.5),
        (r"\bvalue\s+date\b", 2.5),
        (r"\bwithdrawal\s+amt\b", 3.0),
        (r"\bdeposit\s+amt\b", 3.0),
        (r"\bclearing\s+cheque\b", 2.0),
        (r"\bneft\s*[\/\-]?\s*rtgs\b", 2.5),
        (r"ಬ್ಯಾಂಕ್\s+ಖಾತೆ\s+ವಿವರ", 4.5),
        (r"ಬ್ಯಾಂಕ್\s+ವಿವರ", 4.0),
    ],
    "Supporting Document": [
        (r"\bquotation\b", 3.5),
        (r"\bdelivery\s+challan\b", 3.5),
        (r"\bmuster\s+roll\b", 3.5),
        (r"\battendance\s+sheet\b", 3.0),
        (r"\bphotographic\s+evidence\b", 3.0),
        (r"\binspection\s+report\b", 3.0),
        (r"ದಾಖಲೆ", 2.5),
        (r"ಹಾಜರಾತಿ\s+ಪಟ್ಟಿ", 3.5),
    ],
}

CONFIDENCE_THRESHOLD = 0.40  # Minimum confidence required to avoid 'Unknown'


def classify_document_text(text: str) -> Dict[str, Any]:
    """
    Classifies raw document text into one of the 13 defined classes using
    weighted pattern scoring and bilingual keyword recognition.
    """
    if not text or not text.strip():
        return {
            "document_type": "Unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "needs_manual_review": True,
            "explanation": "No extractable text found in document",
            "scores": {},
        }

    lower_text = text.lower()
    raw_scores: Dict[str, float] = {}
    matched_by_class: Dict[str, List[str]] = {}

    for doc_class, rules in CLASS_RULES.items():
        score = 0.0
        matches: List[str] = []
        for pattern, weight in rules:
            found = re.findall(pattern, lower_text, flags=re.IGNORECASE)
            if found:
                score += weight * min(len(found), 3)  # Cap repetitive matches at 3
                matched_label = pattern.replace(r"\b", "").replace("\\", "").strip()
                matches.append(f"{matched_label} (+{weight})")
        if score > 0:
            raw_scores[doc_class] = score
            matched_by_class[doc_class] = matches

    if not raw_scores:
        return {
            "document_type": "Unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "needs_manual_review": True,
            "explanation": "No classification keywords matched",
            "scores": {},
        }

    # Normalize scores to [0.0, 1.0]
    best_class = max(raw_scores, key=raw_scores.get)
    best_score = raw_scores[best_class]

    # Confidence calculation: saturation curve based on top score
    # Score of 8+ gives ~0.90, score of 15+ gives ~0.98
    confidence = round(1.0 - (1.0 / (1.0 + (best_score / 3.5))), 3)

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "document_type": "Unknown",
            "confidence": confidence,
            "matched_keywords": matched_by_class.get(best_class, []),
            "needs_manual_review": True,
            "explanation": f"Low classification confidence ({int(confidence * 100)}% for '{best_class}'); flagged for review.",
            "scores": {k: round(v, 2) for k, v in raw_scores.items()},
        }

    return {
        "document_type": best_class,
        "confidence": confidence,
        "matched_keywords": matched_by_class.get(best_class, []),
        "needs_manual_review": confidence < 0.70,
        "explanation": f"Classified as '{best_class}' based on keywords: {', '.join(matched_by_class.get(best_class, [])[:4])}",
        "scores": {k: round(v, 2) for k, v in raw_scores.items()},
    }
