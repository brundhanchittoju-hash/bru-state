import re
from typing import Optional, Tuple
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from app.models.financial import Vendor, VendorAlias


def normalize_vendor_name(name: str) -> str:
    """Normalize vendor name for robust matching:

    - lowercase & trimmed
    - removes prefixes ('m/s', 'messrs', 'ms')
    - standardizes legal suffixes ('pvt ltd' -> 'private limited', '&' -> 'and')
    - removes special punctuation and collapses whitespace
    """
    if not name:
        return ""

    text = name.lower().strip()

    # Normalize ampersand
    text = text.replace("&", " and ")

    # Remove leading prefixes like M/s, Messrs, Ms.
    text = re.sub(r"^(m\s*/\s*s\.?|messrs\.?|ms\.?)\s+", "", text, flags=re.IGNORECASE)

    # Standardize suffixes
    text = re.sub(r"\bpvt\.?\s*ltd\.?\b", "private limited", text, flags=re.IGNORECASE)
    text = re.sub(r"\bltd\.?\b", "limited", text, flags=re.IGNORECASE)
    text = re.sub(r"\bco\.?\b", "company", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcorp\.?\b", "corporation", text, flags=re.IGNORECASE)
    text = re.sub(r"\binc\.?\b", "incorporated", text, flags=re.IGNORECASE)

    # Strip punctuation except alphanumeric and spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_vendor_similarity(name1: str, name2: str) -> float:
    n1 = normalize_vendor_name(name1)
    n2 = normalize_vendor_name(name2)
    return float(max(fuzz.token_sort_ratio(n1, n2), fuzz.ratio(n1, n2)))


def resolve_vendor(
    db: Session,
    raw_name: str,
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    similarity_threshold: float = 88.0,
) -> Tuple[Optional[Vendor], float, str]:
    """Resolves or matches a vendor from statutory identifiers or name.

    Returns: (Vendor, match_confidence_score, match_status)
    match_status: 'exact_gstin', 'exact_pan', 'exact_name', 'alias_match', 'fuzzy_match', 'new_vendor', 'pending_review'
    """
    if not raw_name and not gstin and not pan:
        return None, 0.0, "none"

    clean_gstin = gstin.strip().upper() if gstin else None
    clean_pan = pan.strip().upper() if pan else None
    norm_name = normalize_vendor_name(raw_name) if raw_name else ""

    # 1. Match by GSTIN if provided
    if clean_gstin:
        vendor_by_gst = db.query(Vendor).filter(Vendor.gstn == clean_gstin, Vendor.deleted_at.is_(None)).first()
        if vendor_by_gst:
            return vendor_by_gst, 1.0, "exact_gstin"

    # 2. Match by PAN if provided
    if clean_pan:
        vendor_by_pan = db.query(Vendor).filter(Vendor.pan == clean_pan, Vendor.deleted_at.is_(None)).first()
        if vendor_by_pan:
            return vendor_by_pan, 1.0, "exact_pan"

    if not norm_name:
        return None, 0.0, "no_name"

    # 3. Check existing vendors and confirmed aliases
    all_vendors = db.query(Vendor).filter(Vendor.deleted_at.is_(None)).all()
    for v in all_vendors:
        if normalize_vendor_name(v.legal_name) == norm_name:
            return v, 1.0, "exact_name"

    all_aliases = db.query(VendorAlias).filter(
        VendorAlias.status == "confirmed",
        VendorAlias.deleted_at.is_(None)
    ).all()
    for alias in all_aliases:
        if normalize_vendor_name(alias.alias_name) == norm_name:
            return alias.vendor, 0.98, "alias_match"

    # 4. Fuzzy match against all vendors and aliases using rapidfuzz
    best_vendor: Optional[Vendor] = None
    best_score: float = 0.0

    for v in all_vendors:
        candidate_norm = normalize_vendor_name(v.legal_name)
        # Combine token_sort_ratio and ratio for robust name matching
        score = max(
            fuzz.token_sort_ratio(norm_name, candidate_norm),
            fuzz.ratio(norm_name, candidate_norm)
        )
        if score > best_score:
            best_score = float(score)
            best_vendor = v

        for alias in v.aliases:
            if alias.status == "confirmed" and alias.deleted_at is None:
                alias_norm = normalize_vendor_name(alias.alias_name)
                ascore = max(
                    fuzz.token_sort_ratio(norm_name, alias_norm),
                    fuzz.ratio(norm_name, alias_norm)
                )
                if ascore > best_score:
                    best_score = float(ascore)
                    best_vendor = v

    # If score is >= similarity_threshold (default 88), link vendor
    if best_score >= similarity_threshold and best_vendor is not None:
        # Check if alias already exists
        existing_alias = db.query(VendorAlias).filter(
            VendorAlias.vendor_id == best_vendor.id,
            VendorAlias.alias_name == raw_name,
            VendorAlias.deleted_at.is_(None)
        ).first()
        if not existing_alias:
            new_alias = VendorAlias(
                vendor_id=best_vendor.id,
                alias_name=raw_name,
                confidence_score=round(best_score / 100.0, 3),
                status="confirmed" if best_score >= 95.0 else "pending_review"
            )
            db.add(new_alias)
            db.flush()
        return best_vendor, round(best_score / 100.0, 3), "fuzzy_match" if best_score >= 95.0 else "pending_review"

    # 5. Create new vendor if not found
    new_vendor = Vendor(
        legal_name=raw_name.strip(),
        gstn=clean_gstin,
        pan=clean_pan,
        is_flagged=False
    )
    db.add(new_vendor)
    db.flush()

    return new_vendor, 1.0, "new_vendor"
