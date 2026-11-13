import hashlib
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.financial import FinancialRecord, RecordLink, Transaction
from app.models.audit_case import AuditCase
from app.services.extraction.effective_value import get_effective_field_value
from app.services.extraction.parser_utils import parse_indian_amount, parse_indian_date
from app.services.verification.vendor_matcher import resolve_vendor


def parse_date_safe(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        dt = parse_indian_date(val)
        if isinstance(dt, datetime):
            return dt.date()
        return dt
    except Exception:
        return None


def parse_amount_safe(val: Optional[str]) -> Decimal:
    if not val:
        return Decimal("0.00")
    try:
        amt, _ = parse_indian_amount(val)
        return amt if amt is not None else Decimal("0.00")
    except Exception:
        return Decimal("0.00")


def build_financial_records_for_case(db: Session, case_id: str) -> List[FinancialRecord]:
    """Idempotently reconstructs all FinancialRecords for a given case

    from processed Documents (using effective field values) and case Transactions.
    """
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        return []

    # 1. Clean up existing links and records for this case
    db.query(RecordLink).filter(RecordLink.case_id == case_id).delete(synchronize_session=False)
    db.query(FinancialRecord).filter(FinancialRecord.case_id == case_id).delete(synchronize_session=False)
    db.flush()

    records: List[FinancialRecord] = []

    # 2. Extract from processed documents
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.deleted_at.is_(None),
        Document.status == "processed"
    ).all()

    for doc in documents:
        # Build map of effective field values
        field_map: Dict[str, str] = {}
        field_id_map: Dict[str, str] = {}
        for f in doc.extracted_fields:
            eff_val = get_effective_field_value(f)
            if eff_val:
                field_map[f.field_name] = eff_val
                field_id_map[f.field_name] = f.id

        doc_type_raw = (doc.document_type or "Supporting Document").lower()
        
        # Determine canonical record_type
        record_type = "supporting_document"
        if "bill" in doc_type_raw or "invoice" in doc_type_raw:
            record_type = "bill"
        elif "voucher" in doc_type_raw:
            record_type = "voucher"
        elif "sanction" in doc_type_raw:
            record_type = "sanction"
        elif "work order" in doc_type_raw:
            record_type = "work_order"
        elif "tender" in doc_type_raw:
            record_type = "tender"
        elif "measurement" in doc_type_raw:
            record_type = "measurement_book"
        elif "completion" in doc_type_raw:
            record_type = "completion_certificate"
        elif "utilization" in doc_type_raw:
            record_type = "utilization_certificate"
        elif "bank" in doc_type_raw:
            record_type = "bank_debit"
        elif "cash book" in doc_type_raw:
            record_type = "cash_book_entry"
        elif "ledger" in doc_type_raw:
            record_type = "ledger_entry"

        # Determine amounts
        total_amt = parse_amount_safe(
            field_map.get("total_amount") or
            field_map.get("amount") or
            field_map.get("sanctioned_amount") or
            field_map.get("contract_value") or
            field_map.get("tender_amount") or
            field_map.get("estimated_amount") or
            field_map.get("passed_for_payment") or
            field_map.get("utilized_amount")
        )
        base_amt = parse_amount_safe(field_map.get("taxable_amount"))
        tax_amt = parse_amount_safe(field_map.get("tax_amount"))
        if tax_amt == Decimal("0.00"):
            cgst = parse_amount_safe(field_map.get("cgst_amount"))
            sgst = parse_amount_safe(field_map.get("sgst_amount"))
            igst = parse_amount_safe(field_map.get("igst_amount"))
            tax_amt = cgst + sgst + igst

        # Determine document number
        doc_num = (
            field_map.get("bill_number") or
            field_map.get("voucher_number") or
            field_map.get("sanction_number") or
            field_map.get("work_order_number") or
            field_map.get("tender_number") or
            field_map.get("mb_number") or
            field_map.get("certificate_number") or
            field_map.get("uc_number") or
            field_map.get("invoice_number") or
            doc.original_filename
        )

        # Determine date
        rec_date = parse_date_safe(
            field_map.get("bill_date") or
            field_map.get("voucher_date") or
            field_map.get("sanction_date") or
            field_map.get("order_date") or
            field_map.get("tender_date") or
            field_map.get("completion_date") or
            field_map.get("uc_date") or
            field_map.get("date")
        )

        # Resolve vendor
        vendor_name = field_map.get("vendor_name")
        gstin = field_map.get("gstin")
        pan = field_map.get("pan")
        vendor_obj = None
        if vendor_name or gstin or pan:
            vendor_obj, _, _ = resolve_vendor(db, raw_name=vendor_name or "", gstin=gstin, pan=pan)

        rec_id = hashlib.sha256(f"{case_id}:doc:{doc.id}:{record_type}:{doc_num}".encode()).hexdigest()[:36]
        rec = FinancialRecord(
            id=rec_id,
            case_id=case_id,
            vendor_id=vendor_obj.id if vendor_obj else None,
            record_type=record_type,
            document_number=doc_num,
            date=rec_date,
            base_amount=base_amt if base_amt > 0 else None,
            tax_amount=tax_amt if tax_amt > 0 else None,
            total_amount=total_amt,
            payment_reference=field_map.get("payment_reference") or field_map.get("utr_number"),
            cheque_number=field_map.get("cheque_number"),
            source_document_id=doc.id,
            source_page=1,
            source_field_ids=json.dumps(list(field_id_map.values())),
            raw_data_json=json.dumps(field_map)
        )
        db.add(rec)
        records.append(rec)

    # 3. Extract from imported case Transactions (e.g. from tabular CSV/XLSX or bank feeds)
    transactions = db.query(Transaction).filter(
        Transaction.case_id == case_id,
        Transaction.deleted_at.is_(None)
    ).all()

    for tx in transactions:
        tx_type = "ledger_entry"
        desc_lower = (tx.description or "").lower()
        v_no = (tx.voucher_no or "").upper()
        if "DEBIT" in v_no or "BANK" in v_no or "RTGS" in v_no or "NEFT" in v_no or "UTR" in v_no:
            tx_type = "bank_debit" if (tx.debit and tx.debit > 0) else "ledger_entry"
        elif "VOUCH" in v_no or "VR" in v_no or tx.voucher_no:
            tx_type = "voucher"
        elif "bank" in desc_lower or "neft" in desc_lower or "rtgs" in desc_lower or "utr" in desc_lower:
            tx_type = "bank_debit" if (tx.debit and tx.debit > 0) else "ledger_entry"
        elif "cash" in desc_lower or tx.payment_mode == "Cash":
            tx_type = "cash_book_entry"

        # Check vendor
        vendor_id = tx.vendor_id
        if not vendor_id and tx.description:
            # Check if vendor mentioned in description
            v_match, _, _ = resolve_vendor(db, raw_name=tx.description[:100])
            if v_match:
                vendor_id = v_match.id

        tx_rec_id = hashlib.sha256(f"{case_id}:tx:{tx.id}:{tx.row_number}".encode()).hexdigest()[:36]
        tx_rec = FinancialRecord(
            id=tx_rec_id,
            case_id=case_id,
            vendor_id=vendor_id,
            record_type=tx_type,
            document_number=tx.voucher_no,
            date=tx.transaction_date,
            base_amount=None,
            tax_amount=None,
            total_amount=Decimal(str(tx.amount)),
            payment_reference=tx.voucher_no,
            cheque_number=None,
            source_document_id=tx.source_document_id,
            source_row=tx.row_number,
            raw_data_json=json.dumps({
                "description": tx.description,
                "scheme_name": tx.scheme_name,
                "debit": str(tx.debit) if tx.debit else None,
                "credit": str(tx.credit) if tx.credit else None,
                "payment_mode": tx.payment_mode
            })
        )
        db.add(tx_rec)
        records.append(tx_rec)

    db.flush()
    return records
