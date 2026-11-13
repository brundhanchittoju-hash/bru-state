import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple, Dict, Any

# ==============================================================================
# Indian Amount Parser & Number Words Cross-Check
# ==============================================================================

# Words to numbers mapping for Indian financial nomenclature
NUMBER_WORDS: Dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}

SCALE_WORDS: Dict[str, int] = {
    "hundred": 100,
    "thousand": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
}


def parse_indian_amount(raw_text: Optional[str]) -> Tuple[Optional[Decimal], Dict[str, Any]]:
    """
    Parses Indian financial currency strings into a Decimal.
    Handles ₹, Rs., Rs, Rs/-, INR, lakh/crore comma grouping, negative brackets, Dr/Cr suffixes.
    Returns (parsed_decimal, metadata_dict).
    """
    if not raw_text or not isinstance(raw_text, str):
        return None, {"error": "Empty input"}

    cleaned = raw_text.strip()
    is_negative = False
    is_credit = False
    is_debit = False

    # Check parentheses for negative values e.g. (1,23,456.00)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()

    # Check Dr / Cr suffix
    if re.search(r"\b(cr|credit)\b", cleaned, re.IGNORECASE):
        is_credit = True
        cleaned = re.sub(r"\b(cr|credit)\b", "", cleaned, flags=re.IGNORECASE).strip()
    elif re.search(r"\b(dr|debit)\b", cleaned, re.IGNORECASE):
        is_debit = True
        is_negative = True
        cleaned = re.sub(r"\b(dr|debit)\b", "", cleaned, flags=re.IGNORECASE).strip()

    # Remove currency symbols and terms
    cleaned = re.sub(r"[₹\u20b9]", "", cleaned)
    cleaned = re.sub(r"\b(inr|rs\.?|rupees|rupee)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"/-\s*$", "", cleaned).strip()

    # Check for leading minus
    if cleaned.startswith("-"):
        is_negative = True
        cleaned = cleaned[1:].strip()

    # Remove commas and clean spaces
    cleaned = cleaned.replace(",", "").strip()

    # Match numeric pattern: digits with optional decimal part
    num_match = re.search(r"^(\d+(?:\.\d{1,4})?)$", cleaned)
    if not num_match:
        # Try extracting the primary numeric substring
        fallback_match = re.search(r"(\d+(?:\.\d{1,4})?)", cleaned)
        if not fallback_match:
            return None, {"error": f"Could not parse numeric amount from '{raw_text}'"}
        num_str = fallback_match.group(1)
    else:
        num_str = num_match.group(1)

    try:
        val = Decimal(num_str)
        if is_negative:
            val = -val
        return val, {
            "is_negative": is_negative,
            "is_credit": is_credit,
            "is_debit": is_debit,
            "raw_text": raw_text,
        }
    except InvalidOperation:
        return None, {"error": f"Invalid decimal conversion for '{num_str}'"}


def words_to_indian_amount(words_str: Optional[str]) -> Optional[Decimal]:
    """
    Parses an Indian amount in words into a Decimal.
    Example: 'Rupees Four Lakh Eighty Five Thousand Seven Hundred Only' -> 485700.00
    """
    if not words_str or not isinstance(words_str, str):
        return None

    cleaned = words_str.lower()
    cleaned = re.sub(r"\b(rupees|rupee|only|and|paisa|paise)\b", " ", cleaned)
    tokens = re.findall(r"[a-z]+", cleaned)
    if not tokens:
        return None

    total = 0
    current_chunk = 0

    for token in tokens:
        if token in NUMBER_WORDS:
            current_chunk += NUMBER_WORDS[token]
        elif token in SCALE_WORDS:
            scale = SCALE_WORDS[token]
            if current_chunk == 0:
                current_chunk = 1
            if scale >= 100_000:  # lakh or crore
                total += current_chunk * scale
                current_chunk = 0
            elif scale == 1000:
                total += current_chunk * 1000
                current_chunk = 0
            elif scale == 100:
                current_chunk *= 100

    total += current_chunk
    return Decimal(total) if total > 0 else None


def cross_check_amount_with_words(amount_num: Decimal, words_str: Optional[str]) -> Dict[str, Any]:
    """
    Cross-checks a numeric amount against its spelled-out words equivalent.
    Returns a dict with match status and discrepancy flag.
    """
    if not words_str:
        return {"words_present": False, "match": True, "discrepancy": False}

    words_val = words_to_indian_amount(words_str)
    if words_val is None:
        return {"words_present": True, "match": False, "parsed_words": None, "discrepancy": True}

    # Compare integer parts (ignore minor paise differences unless explicit)
    num_int = int(abs(amount_num))
    words_int = int(words_val)
    match = (num_int == words_int)

    return {
        "words_present": True,
        "match": match,
        "amount_numeric": float(amount_num),
        "amount_from_words": float(words_val),
        "discrepancy": not match,
    }


# ==============================================================================
# Indian Date Parser
# ==============================================================================

MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def parse_indian_date(raw_text: Optional[str]) -> Optional[date]:
    """
    Parses Indian date formats into datetime.date with strict validity checks.
    Supported: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, '12 Mar 2025', '12-Mar-2025', yyyy-mm-dd.
    Rejects invalid calendar dates (e.g., 31-02-2024).
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = raw_text.strip().rstrip(".,;")

    # 1. Check textual month: '12 Mar 2025', '12-Mar-2025', '12 March 2025'
    text_month_match = re.search(
        r"\b(\d{1,2})[\s\-\/\.]*([A-Za-z]{3,9})[\s\-\/\.]*(\d{4})\b",
        cleaned,
    )
    if text_month_match:
        day_str, month_str, year_str = text_month_match.groups()
        month_key = month_str.lower()
        if month_key in MONTH_NAMES:
            month = MONTH_NAMES[month_key]
            try:
                d = date(int(year_str), month, int(day_str))
                if 1990 <= d.year <= 2100:
                    return d
            except ValueError:
                return None

    # 2. Check numeric patterns: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
    dmy_match = re.search(r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b", cleaned)
    if dmy_match:
        day_str, month_str, year_str = dmy_match.groups()
        try:
            d = date(int(year_str), int(month_str), int(day_str))
            if 1990 <= d.year <= 2100:
                return d
        except ValueError:
            return None

    # 3. Check ISO: yyyy-mm-dd
    iso_match = re.search(r"\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b", cleaned)
    if iso_match:
        year_str, month_str, day_str = iso_match.groups()
        try:
            d = date(int(year_str), int(month_str), int(day_str))
            if 1990 <= d.year <= 2100:
                return d
        except ValueError:
            return None

    return None


# ==============================================================================
# Statutory Identifier Validators (GSTIN, PAN, IFSC)
# ==============================================================================

GSTIN_CHAR_MAP = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def calculate_gstin_checksum(gstin_14: str) -> str:
    """
    Computes the 15th checksum character of a 14-character Indian GSTIN prefix.
    Uses the official Luhn-variant mod 36 algorithm.
    """
    total = 0
    for idx, char in enumerate(gstin_14.upper()):
        char_val = GSTIN_CHAR_MAP.find(char)
        if char_val == -1:
            return ""
        # Multiplier alternates: 1 for odd index (1st, 3rd...), 2 for even index (2nd, 4th...)
        multiplier = 2 if (idx % 2 == 1) else 1
        product = char_val * multiplier
        quotient = product // 36
        remainder = product % 36
        total += quotient + remainder

    remainder_total = total % 36
    checksum_val = (36 - remainder_total) % 36
    return GSTIN_CHAR_MAP[checksum_val]


def validate_gstin(gstin: Optional[str]) -> Tuple[bool, str]:
    """
    Validates a 15-character Indian GSTIN.
    Checks regex structure and checksum integrity.
    """
    if not gstin or not isinstance(gstin, str):
        return False, "GSTIN cannot be empty"

    cleaned = gstin.strip().upper()
    if len(cleaned) != 15:
        return False, f"GSTIN must be 15 characters long (got {len(cleaned)})"

    # Regex: 2 digits state code, 5 letters PAN, 4 digits, 1 letter, 1 alphanumeric (entity #), 'Z', 1 checksum char
    regex = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if not re.match(regex, cleaned):
        return False, "Invalid GSTIN pattern format"

    # Verify checksum character
    expected_check = calculate_gstin_checksum(cleaned[:14])
    if cleaned[14] != expected_check:
        return False, f"Checksum mismatch: expected '{expected_check}', got '{cleaned[14]}'"

    return True, "Valid GSTIN"


def validate_pan(pan: Optional[str]) -> Tuple[bool, str]:
    """
    Validates a 10-character Indian Permanent Account Number (PAN).
    Structure: 5 uppercase letters, 4 digits, 1 uppercase letter.
    4th char represents entity type: P (individual), C (company), F (firm), H (HUF), G (gov), T (trust), etc.
    """
    if not pan or not isinstance(pan, str):
        return False, "PAN cannot be empty"

    cleaned = pan.strip().upper()
    if len(cleaned) != 10:
        return False, f"PAN must be 10 characters long (got {len(cleaned)})"

    regex = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    if not re.match(regex, cleaned):
        return False, "Invalid PAN pattern (must be 5 letters, 4 digits, 1 letter)"

    entity_code = cleaned[3]
    known_entities = {
        "P": "Individual", "C": "Company", "H": "HUF", "F": "Firm",
        "A": "Association", "T": "Trust", "B": "Body of Individuals",
        "L": "Local Authority", "J": "Artificial Juridical Person", "G": "Government",
    }
    entity_desc = known_entities.get(entity_code, "Other")

    return True, f"Valid PAN ({entity_desc})"


def validate_ifsc(ifsc: Optional[str]) -> Tuple[bool, str]:
    """
    Validates an 11-character Indian Financial System Code (IFSC).
    Structure: 4 letters (Bank code), 5th char strictly '0', 6 alphanumeric branch code.
    """
    if not ifsc or not isinstance(ifsc, str):
        return False, "IFSC cannot be empty"

    cleaned = ifsc.strip().upper()
    if len(cleaned) != 11:
        return False, f"IFSC must be 11 characters long (got {len(cleaned)})"

    regex = r"^[A-Z]{4}0[A-Z0-9]{6}$"
    if not re.match(regex, cleaned):
        if len(cleaned) >= 5 and cleaned[4] != '0':
            return False, "5th character of IFSC must strictly be '0'"
        return False, "Invalid IFSC pattern"

    return True, "Valid IFSC"
