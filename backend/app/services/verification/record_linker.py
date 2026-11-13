import json
from datetime import timedelta
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models.financial import FinancialRecord, RecordLink


def normalize_ref_str(ref: str) -> str:
    if not ref:
        return ""
    import re
    return re.sub(r"[\s\-_/]", "", ref).lower().lstrip("0")


def link_financial_records_for_case(db: Session, case_id: str) -> List[RecordLink]:
    """Links related FinancialRecords along standard government expenditure chains:

    Sanction -> Work Order -> Bill -> Voucher -> Ledger Entry -> Bank Debit

    Priority:
    1. Explicit reference (document_number / payment_reference / cheque) -> confidence 1.0
    2. Exact Vendor + Exact Amount + Date window (+/- 45 days) -> confidence 0.90
    3. Exact Vendor + Amount within tolerance (+/- 1.0) -> confidence 0.75
    """
    # 1. Clean up existing links for this case
    db.query(RecordLink).filter(RecordLink.case_id == case_id).delete(synchronize_session=False)
    db.flush()

    records = db.query(FinancialRecord).filter(
        FinancialRecord.case_id == case_id,
        FinancialRecord.deleted_at.is_(None)
    ).all()

    bills = [r for r in records if r.record_type == "bill"]
    vouchers = [r for r in records if r.record_type == "voucher"]
    ledgers = [r for r in records if r.record_type in ("ledger_entry", "cash_book_entry")]
    banks = [r for r in records if r.record_type == "bank_debit"]
    sanctions = [r for r in records if r.record_type == "sanction"]
    work_orders = [r for r in records if r.record_type == "work_order"]

    links: List[RecordLink] = []

    def create_link(src: FinancialRecord, tgt: FinancialRecord, ltype: str, method: str, conf: float, meta: dict):
        link = RecordLink(
            case_id=case_id,
            source_record_id=src.id,
            target_record_id=tgt.id,
            link_type=ltype,
            match_method=method,
            confidence=conf,
            metadata_json=json.dumps(meta)
        )
        db.add(link)
        links.append(link)

    # 1. Link Bill -> Voucher
    matched_voucher_ids = set()
    for bill in bills:
        bill_norm = normalize_ref_str(bill.document_number or "")
        best_v = None
        best_method = None
        best_conf = 0.0

        for v in vouchers:
            v_ref_norm = normalize_ref_str(v.payment_reference or v.document_number or "")
            # Strategy A: Explicit reference
            if bill_norm and v_ref_norm and (bill_norm in v_ref_norm or v_ref_norm in bill_norm):
                best_v = v
                best_method = "explicit_reference"
                best_conf = 1.0
                break

            # Strategy B: Same vendor + Same amount + Date window
            if bill.vendor_id and v.vendor_id and bill.vendor_id == v.vendor_id:
                amt_diff = abs(bill.total_amount - v.total_amount)
                if amt_diff <= Decimal("1.00"):
                    date_ok = True
                    if bill.date and v.date:
                        date_ok = abs((v.date - bill.date).days) <= 60
                    if date_ok and best_conf < 0.90:
                        best_v = v
                        best_method = "vendor_amount_date"
                        best_conf = 0.90
                elif best_conf < 0.60:
                    # Same vendor amount mismatch
                    best_v = v
                    best_method = "vendor_partial"
                    best_conf = 0.60

        if best_v:
            matched_voucher_ids.add(best_v.id)
            create_link(bill, best_v, "bill_to_voucher", best_method, best_conf, {
                "bill_number": bill.document_number,
                "voucher_number": best_v.document_number,
                "bill_amount": str(bill.total_amount),
                "voucher_amount": str(best_v.total_amount)
            })

    # 2. Link Voucher -> Bank Debit / Ledger Entry
    matched_bank_ids = set()
    for v in vouchers:
        v_norm = normalize_ref_str(v.document_number or "")
        # Link to Bank
        for b in banks:
            if b.id in matched_bank_ids:
                continue
            b_norm = normalize_ref_str(b.payment_reference or b.document_number or "")
            b_meta_str = b.raw_data_json or ""
            # Strategy A: Explicit reference
            if v_norm and (v_norm in b_norm or b_norm in v_norm or v_norm in normalize_ref_str(b_meta_str)):
                create_link(v, b, "voucher_to_bank", "explicit_reference", 1.0, {
                    "voucher_number": v.document_number,
                    "bank_reference": b.payment_reference,
                    "voucher_amount": str(v.total_amount),
                    "bank_amount": str(b.total_amount)
                })
                matched_bank_ids.add(b.id)
                break
            # Strategy B: Same vendor + Same amount + Date window
            elif (v.vendor_id == b.vendor_id or not b.vendor_id or not v.vendor_id) and abs(v.total_amount - b.total_amount) <= Decimal("1.00"):
                date_ok = True
                if v.date and b.date:
                    date_ok = abs((b.date - v.date).days) <= 45
                if date_ok:
                    create_link(v, b, "voucher_to_bank", "amount_date_match", 0.85, {
                        "voucher_number": v.document_number,
                        "bank_reference": b.payment_reference,
                        "voucher_amount": str(v.total_amount),
                        "bank_amount": str(b.total_amount)
                    })
                    matched_bank_ids.add(b.id)
                    break

        # Link to Ledger Entry
        for l in ledgers:
            l_norm = normalize_ref_str(l.document_number or l.payment_reference or "")
            if v_norm and l_norm and (v_norm in l_norm or l_norm in v_norm):
                create_link(v, l, "voucher_to_ledger", "explicit_reference", 1.0, {
                    "voucher_number": v.document_number,
                    "ledger_voucher": l.document_number,
                    "voucher_amount": str(v.total_amount),
                    "ledger_amount": str(l.total_amount)
                })
                break

    # 3. Link Sanction -> Work Order
    for s in sanctions:
        for wo in work_orders:
            create_link(s, wo, "sanction_to_work_order", "case_project_chain", 0.90, {
                "sanction_number": s.document_number,
                "work_order_number": wo.document_number,
                "sanction_amount": str(s.total_amount),
                "contract_value": str(wo.total_amount)
            })

    # 4. Link Work Order -> Bill (matching vendor or explicit reference)
    for wo in work_orders:
        wo_norm = normalize_ref_str(wo.document_number or "")
        for b in bills:
            b_meta_str = b.raw_data_json or ""
            is_match = False
            if wo_norm and wo_norm in normalize_ref_str(b_meta_str):
                is_match = True
            elif wo.vendor_id and b.vendor_id and wo.vendor_id == b.vendor_id:
                is_match = True
            elif len(work_orders) == 1:
                is_match = True

            if is_match:
                create_link(wo, b, "work_order_to_bill", "case_project_chain", 0.85, {
                    "work_order_number": wo.document_number,
                    "bill_number": b.document_number,
                    "contract_value": str(wo.total_amount),
                    "bill_amount": str(b.total_amount)
                })

    db.flush()
    return links
