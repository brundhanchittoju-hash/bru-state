import csv
import io
import re
from datetime import date
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import openpyxl
from app.services.extraction.parser_utils import parse_indian_amount, parse_indian_date

# ==============================================================================
# Header Synonym Rules for Indian Banking & Audit Ledgers
# ==============================================================================

SYNONYMS: Dict[str, List[str]] = {
    "date": [
        "date", "txn date", "transaction date", "value date", "posting date",
        "trans date", "ದಿನಾಂಕ", "dt"
    ],
    "description": [
        "description", "particulars", "narration", "remarks", "details",
        "transaction details", "transaction remarks", "ವಿವರ"
    ],
    "reference": [
        "ref no", "reference", "reference no", "chq no", "cheque no", "utr",
        "utr no", "txn id", "instrument no", "voucher no", "vr no"
    ],
    "debit": [
        "debit", "dr", "withdrawal", "withdrawals", "payment", "payments",
        "debit amount", "ಖರ್ಚು"
    ],
    "credit": [
        "credit", "cr", "deposit", "deposits", "receipt", "receipts",
        "credit amount", "ಜಮೆ"
    ],
    "balance": [
        "balance", "closing balance", "net balance", "available balance",
        "ಶುಲ್ಕ", "ಬಾಕಿ"
    ],
    "amount": [
        "amount", "txn amount", "total", "ಮೊತ್ತ"
    ]
}


def detect_column_mapping(headers: List[str]) -> Tuple[Dict[str, str], float]:
    """
    Auto-detects mapping from sheet headers to canonical transaction fields.
    Returns (mapping_dict, confidence_score).
    """
    mapping: Dict[str, str] = {}
    matched_count = 0

    lower_headers = [h.strip().lower() for h in headers]

    for canonical, syn_list in SYNONYMS.items():
        for syn in syn_list:
            for idx, h in enumerate(lower_headers):
                if syn == h or re.search(rf"\b{re.escape(syn)}\b", h):
                    if canonical not in mapping:
                        mapping[canonical] = headers[idx]
                        matched_count += 1
                        break
            if canonical in mapping:
                break

    # Confidence calculation: must have at least date and (amount or debit/credit)
    essential_present = "date" in mapping and ("amount" in mapping or "debit" in mapping or "credit" in mapping)
    confidence = 0.0
    if essential_present:
        confidence = min(0.95, round(0.50 + (matched_count * 0.10), 2))
    elif matched_count > 0:
        confidence = 0.35

    return mapping, confidence


def parse_tabular_content(
    file_bytes: bytes,
    mime_type: str,
    custom_mapping: Optional[Dict[str, str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Parses CSV or Excel (.xlsx) file into structured transaction rows.
    Supports auto-detected or user-supplied custom mapping.
    Handles Indian numbers, Dr/Cr suffixes, and multiple date formats.
    """
    rows_data: List[Dict[str, Any]] = []
    headers: List[str] = []

    # 1. Parse into raw header and row string lists
    if "sheet" in mime_type or "excel" in mime_type or mime_type.endswith(".sheet"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        raw_rows = list(sheet.iter_rows(values_only=True))
        if not raw_rows:
            return {"headers": [], "rows": [], "mapping": {}, "confidence": 0.0}

        headers = [str(cell).strip() if cell is not None else f"Col_{i+1}" for i, cell in enumerate(raw_rows[0])]
        data_rows = raw_rows[1:]
        for r in data_rows:
            if not any(r):
                continue
            rows_data.append({headers[i]: str(cell).strip() if cell is not None else "" for i, cell in enumerate(r)})
    else:
        # Default CSV
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")
        reader = csv.reader(io.StringIO(text))
        all_lines = list(reader)
        if not all_lines:
            return {"headers": [], "rows": [], "mapping": {}, "confidence": 0.0}

        headers = [h.strip() if h.strip() else f"Col_{i+1}" for i, h in enumerate(all_lines[0])]
        for line in all_lines[1:]:
            if not any(line):
                continue
            rows_data.append({headers[i]: line[i].strip() if i < len(line) else "" for i in range(len(headers))})

    # 2. Determine Column Mapping
    if custom_mapping:
        mapping = custom_mapping
        confidence = 1.0
    else:
        mapping, confidence = detect_column_mapping(headers)

    # 3. Process Rows into Canonical Transaction Format
    processed_transactions: List[Dict[str, Any]] = []
    preview_limit = limit if limit is not None else len(rows_data)

    for idx, row in enumerate(rows_data[:preview_limit]):
        # Date
        date_col = mapping.get("date")
        raw_date = row.get(date_col, "") if date_col else ""
        parsed_dt = parse_indian_date(raw_date)

        # Description
        desc_col = mapping.get("description")
        description = row.get(desc_col, "") if desc_col else ""

        # Reference
        ref_col = mapping.get("reference")
        reference = row.get(ref_col, f"ROW-{idx+1}") if ref_col else f"ROW-{idx+1}"

        # Debit / Credit / Balance
        debit_col = mapping.get("debit")
        credit_col = mapping.get("credit")
        balance_col = mapping.get("balance")
        amount_col = mapping.get("amount")

        debit_amt, _ = parse_indian_amount(row.get(debit_col)) if debit_col else (None, {})
        credit_amt, _ = parse_indian_amount(row.get(credit_col)) if credit_col else (None, {})
        balance_amt, _ = parse_indian_amount(row.get(balance_col)) if balance_col else (None, {})

        # Compute net amount: if debit present, net is debit; else credit; or amount col
        if debit_amt is not None and debit_amt > 0:
            net_amt = debit_amt
            tx_type = "debit"
        elif credit_amt is not None and credit_amt > 0:
            net_amt = credit_amt
            tx_type = "credit"
        elif amount_col:
            amt, meta = parse_indian_amount(row.get(amount_col))
            net_amt = amt if amt is not None else Decimal("0.00")
            tx_type = "debit" if meta.get("is_debit") else "credit"
        else:
            net_amt = Decimal("0.00")
            tx_type = "unknown"

        processed_transactions.append({
            "row_number": idx + 1,
            "raw_row": row,
            "transaction_date": parsed_dt.isoformat() if parsed_dt else date.today().isoformat(),
            "voucher_no": reference or f"TXN-{idx+1}",
            "description": description,
            "amount": float(net_amt),
            "debit": float(debit_amt) if debit_amt is not None else None,
            "credit": float(credit_amt) if credit_amt is not None else None,
            "balance": float(balance_amt) if balance_amt is not None else None,
            "type": tx_type,
        })

    return {
        "headers": headers,
        "mapping": mapping,
        "confidence": confidence,
        "total_rows": len(rows_data),
        "transactions": processed_transactions,
    }
