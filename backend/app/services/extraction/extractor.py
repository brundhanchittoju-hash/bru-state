import re
import json
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from app.services.extraction.parser_utils import (
    parse_indian_amount,
    parse_indian_date,
    validate_gstin,
    validate_pan,
    validate_ifsc,
    cross_check_amount_with_words,
)

# ==============================================================================
# Field Extraction Rules with Priority Patterns & Label Keywords
# ==============================================================================

FIELD_RULES = {
    "bill_number": {
        "patterns": [
            r"(?:invoice\s*(?:no|number|#|\.)|bill\s*(?:no|number|#|\.)|inv\s*no\.?|ಬಿಲ್\s*ಸಂಖ್ಯೆ)[\s\:\-]+([A-Za-z0-9\-\/]{3,30})",
            r"\b(?:inv|bill)[\s\:\-\/]+([0-9A-Za-z]+[\/\-][0-9A-Za-z\-\/]+)\b",
        ],
        "category": "Identifiers",
    },
    "voucher_number": {
        "patterns": [
            r"(?:payment\s+voucher\s*(?:no|number|#|\.)|voucher\s*(?:no|number|#|\.)|vr\s*no\.?|ರಶೀದಿ\s*ಸಂಖ್ಯೆ)[\s\:\-]+([A-Za-z0-9\-\/]{2,25})",
            r"\b(?:voucher|vr)[\s\:\-\/]+([0-9A-Za-z]+[\/\-][0-9A-Za-z\-\/]+)\b",
        ],
        "category": "Identifiers",
    },
    "work_order_number": {
        "patterns": [
            r"(?:work\s+order\s*(?:no|number|#|\.)|wo\s*no\.?|job\s+order\s*no\.?|ಕಾರ್ಯಾದೇಶ\s*ಸಂಖ್ಯೆ)[\s\:\-]+([A-Za-z0-9\-\/\.]{3,35})",
        ],
        "category": "Identifiers",
    },
    "sanction_number": {
        "patterns": [
            r"(?:administrative\s+sanction\s*(?:no|number|#|\.)|sanction\s*(?:order\s*)?(?:no|number|#|\.)|as\s*no\.?|ts\s*no\.?|ಮಂಜೂರಾತಿ\s*ಸಂಖ್ಯೆ)[\s\:\-]+([A-Za-z0-9\-\/\.]{3,35})",
            r"(?:g\.?o\.?\s*(?:no|#|\.))[\s\:\-]+([A-Za-z0-9\-\/\.]{3,30})",
        ],
        "category": "Identifiers",
    },
    "tender_number": {
        "patterns": [
            r"(?:tender\s*(?:notification\s*)?(?:no|number|#|\.)|nit\s*(?:no|#|\.)|ind\s*no\.?|ಟೆಂಡರ್\s*ಸಂಖ್ಯೆ)[\s\:\-]+([A-Za-z0-9\-\/\.]{3,35})",
        ],
        "category": "Identifiers",
    },
    "gstin": {
        "patterns": [
            r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b",
            r"(?:gstin|gst\s*no\.?|gst)[\s\:\-]+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b",
        ],
        "category": "Parties",
        "validator": validate_gstin,
    },
    "pan": {
        "patterns": [
            r"(?:pan\s*(?:no|number)?|pan)[\s\:\-]+([A-Z]{5}[0-9]{4}[A-Z]{1})\b",
            r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b",
        ],
        "category": "Parties",
        "validator": validate_pan,
    },
    "ifsc": {
        "patterns": [
            r"(?:ifsc\s*(?:code)?|ifsc)[\s\:\-]+([A-Z]{4}0[A-Z0-9]{6})\b",
            r"\b([A-Z]{4}0[A-Z0-9]{6})\b",
        ],
        "category": "Banking",
        "validator": validate_ifsc,
    },
    "bank_account": {
        "patterns": [
            r"(?:a\/c\s*(?:no|number)?|account\s*(?:no|number)?|bank\s*a\/c)[\s\:\-]+([0-9]{9,18})\b",
            r"\baccount[\s\:\.]+([0-9]{9,18})\b",
        ],
        "category": "Banking",
    },
    "payment_ref": {
        "patterns": [
            r"(?:utr\s*(?:no|number)?|neft\s*ref|rtgs\s*ref|ref\s*no)[\s\:\-]+([A-Za-z0-9]{8,25})\b",
        ],
        "category": "Banking",
    },
    "cheque_number": {
        "patterns": [
            r"(?:cheque\s*(?:no|number)?|chq\s*no\.?)[\s\:\-]+([0-9]{6})\b",
        ],
        "category": "Banking",
    },
    "amount": {
        "patterns": [
            r"(?:grand\s+total|total\s+amount|invoice\s+total|net\s+payable|passed\s+for(?:\s+payment)?|sanctioned\s+estimate|contract\s+amount|estimated\s+cost|final\s+bill(?:\s+amount)?|bill\s*\/\s*claim|ಒಟ್ಟು\s+ಮೊತ್ತ)[\s\:\-]+(?:₹|rs\.?|inr|i)?[\s]*([\d\,]+(?:\.\d{1,2})?[\s]*(?:\/\-|dr|cr)?)",
            r"(?:total|amount|ಮೊತ್ತ)[\s\:\-]+(?:₹|rs\.?|inr|i)?[\s]*([\d\,]+(?:\.\d{1,2})?[\s]*(?:\/\-)?)",
        ],
        "category": "Amounts and Tax",
        "is_amount": True,
    },
    "gst_amount": {
        "patterns": [
            r"(?:total\s+gst|gst\s+amount|cgst\s*\+\s*sgst|igst\s+amount)[\s\:\-]+(?:₹|rs\.?|inr)?[\s]*([\d\,]+(?:\.\d{1,2})?)",
        ],
        "category": "Amounts and Tax",
        "is_amount": True,
    },
    "gst_rate": {
        "patterns": [
            r"(?:gst\s*rate|rate\s*of\s*gst|gst\s*@)[\s\:\-]+(\d{1,2}(?:\.\d{1,2})?)\s*%",
            r"\b(\d{1,2})\s*%\s*gst\b",
        ],
        "category": "Amounts and Tax",
    },
    "tax": {
        "patterns": [
            r"(?:total\s+tax|tax\s+amount|tds\s+deducted)[\s\:\-]+(?:₹|rs\.?|inr)?[\s]*([\d\,]+(?:\.\d{1,2})?)",
        ],
        "category": "Amounts and Tax",
        "is_amount": True,
    },
    "invoice_date": {
        "patterns": [
            r"(?:invoice\s*date|bill\s*date|ದಿನಾಂಕ)[\s\:\-]+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{4}|[0-9]{1,2}[\s\-\/]+[A-Za-z]{3,9}[\s\-\/]+[0-9]{4})",
        ],
        "category": "Dates",
        "is_date": True,
    },
    "document_date": {
        "patterns": [
            r"(?:dated?|date)[\s\:\-]+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{4}|[0-9]{1,2}[\s\-\/]+[A-Za-z]{3,9}[\s\-\/]+[0-9]{4})",
            r"\b([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{4})\b",
        ],
        "category": "Dates",
        "is_date": True,
    },
    "vendor_name": {
        "patterns": [
            r"(?:m\/s\.?|vendor|contractor|supplier|ಪೂರೈಕೆದಾರರು)[\s\:\-]+([A-Za-z0-9\s\.\,\&]{3,50})(?:\n|\r|gstin|pan)",
            r"(?:issued\s+by|name\s+of\s+firm)[\s\:\-]+([A-Za-z0-9\s\.\,\&]{3,50})(?:\n|\r)",
        ],
        "category": "Parties",
    },
    "department": {
        "patterns": [
            r"(?:department|dept|directorate)[\s\:\-]+([A-Za-z0-9\s\.\,\&]{3,60})(?:\n|\r)",
            r"(zilla\s+panchayat[\sA-Za-z]*|taluk\s+panchayat[\sA-Za-z]*|gram\s+panchayat[\sA-Za-z]*)",
        ],
        "category": "Parties",
    },
    "project_name": {
        "patterns": [
            r"(?:name\s+of\s+work|work\s+name|project|ಕಾಮಗಾರಿಯ\s+ಹೆಸರು)[\s\:\-]+([A-Za-z0-9\s\.\,\(\)\/\-]{5,90})(?:\n|\r|estimate)",
        ],
        "category": "Identifiers",
    },
}


def extract_fields_from_text(
    pages_text: List[Dict[str, Any]],
    document_type: str = "Unknown",
    ocr_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Extracts 20 Indian financial statutory fields from page text records.
    Computes deterministic confidence scores based on:
      - Pattern specificity (exact label match vs broad fallback)
      - Validator verification (GSTIN/PAN/IFSC checksums)
      - Proximity to field headers
      - Amount in words cross-verification
    """
    extracted_results: Dict[str, Dict[str, Any]] = {}

    # Extract amount-in-words first for cross-check
    words_match_str: Optional[str] = None
    for p in pages_text:
        text = p.get("text", "")
        w_match = re.search(
            r"(?:rupees?|amount\s+in\s+words)[\s\:\-]+([A-Za-z\s]+)(?:only|\.|\n)",
            text,
            flags=re.IGNORECASE,
        )
        if w_match:
            words_match_str = w_match.group(1).strip()
            break

    for page_info in pages_text:
        page_num = page_info.get("page_number", 1)
        page_text = page_info.get("text", "")
        word_boxes = page_info.get("word_boxes", [])

        for field_name, rule_cfg in FIELD_RULES.items():
            if field_name in extracted_results:
                continue  # Field already extracted with higher priority on earlier page

            patterns = rule_cfg.get("patterns", [])
            validator = rule_cfg.get("validator")
            is_amount = rule_cfg.get("is_amount", False)
            is_date = rule_cfg.get("is_date", False)

            for pattern_idx, pattern in enumerate(patterns):
                match = re.search(pattern, page_text, flags=re.IGNORECASE | re.MULTILINE)
                if not match:
                    continue

                raw_value = match.group(1).strip() if match.groups() else match.group(0).strip()
                extracted_value = raw_value
                validation_status = "not_checked"
                validation_message = None
                base_confidence = 0.85 if pattern_idx == 0 else 0.70

                # Amount parsing & cross-verification
                if is_amount:
                    parsed_amt, meta = parse_indian_amount(raw_value)
                    if parsed_amt is not None:
                        extracted_value = f"{parsed_amt:.2f}"
                        # Check words if available for main 'amount'
                        if field_name == "amount" and words_match_str:
                            cross_check = cross_check_amount_with_words(parsed_amt, words_match_str)
                            if cross_check["words_present"]:
                                if cross_check["match"]:
                                    base_confidence = min(0.98, base_confidence + 0.10)
                                    validation_status = "valid"
                                    validation_message = "Numeric amount matches amount-in-words"
                                else:
                                    base_confidence = max(0.50, base_confidence - 0.25)
                                    validation_status = "invalid"
                                    validation_message = f"Discrepancy: numeric ({parsed_amt}) != words ({cross_check['amount_from_words']})"
                    else:
                        base_confidence = 0.35

                # Date parsing
                elif is_date:
                    parsed_dt = parse_indian_date(raw_value)
                    if parsed_dt is not None:
                        extracted_value = parsed_dt.isoformat()
                        validation_status = "valid"
                        base_confidence = min(0.95, base_confidence + 0.10)
                    else:
                        base_confidence = 0.40
                        validation_status = "invalid"
                        validation_message = "Unrecognized date format"

                # Checksum / Structure Validation
                elif validator:
                    is_valid, msg = validator(raw_value)
                    validation_status = "valid" if is_valid else "invalid"
                    validation_message = msg
                    if is_valid:
                        base_confidence = min(0.98, base_confidence + 0.15)
                    else:
                        base_confidence = max(0.40, base_confidence - 0.30)

                # Find approximate bounding box from word coordinates if available
                bbox = None
                if word_boxes:
                    bbox = _find_bounding_box_for_text(raw_value, word_boxes)

                # Slightly reduce confidence if extracted via OCR fallback instead of digital text layer
                final_confidence = round(base_confidence - (0.05 if ocr_mode else 0.0), 2)

                extracted_results[field_name] = {
                    "field_name": field_name,
                    "category": rule_cfg.get("category", "General"),
                    "original_text": match.group(0).strip(),
                    "extracted_value": extracted_value,
                    "confidence": final_confidence,
                    "source_page": page_num,
                    "bbox": json.dumps(bbox) if bbox else None,
                    "extractor": "ocr" if ocr_mode else "rule_parser",
                    "validation_status": validation_status,
                    "validation_message": validation_message,
                }
                break  # Matched highest priority pattern for this field

    return list(extracted_results.values())


def _find_bounding_box_for_text(target: str, word_boxes: List[Dict[str, Any]]) -> Optional[List[float]]:
    """
    Locates word bounding boxes in the normalized page coordinate space and
    computes an enclosing bounding box [x0, y0, x1, y1] (0.0 to 1.0 normalized).
    """
    clean_target = re.sub(r"[^\w]", "", target).lower()
    if not clean_target:
        return None

    matched_boxes = []
    for wb in word_boxes:
        w_text = re.sub(r"[^\w]", "", wb.get("text", "")).lower()
        if w_text and (w_text in clean_target or clean_target in w_text):
            box = wb.get("bbox")  # [x0, y0, x1, y1]
            if box and len(box) == 4:
                matched_boxes.append(box)

    if not matched_boxes:
        return None

    min_x = min(b[0] for b in matched_boxes)
    min_y = min(b[1] for b in matched_boxes)
    max_x = max(b[2] for b in matched_boxes)
    max_y = max(b[3] for b in matched_boxes)
    return [round(min_x, 4), round(min_y, 4), round(max_x, 4), round(max_y, 4)]
