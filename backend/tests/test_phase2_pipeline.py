import io
import json
import os
from decimal import Decimal
import pytest
from app.services.extraction.parser_utils import (
    parse_indian_amount,
    parse_indian_date,
    validate_gstin,
    validate_pan,
    validate_ifsc,
    words_to_indian_amount,
    cross_check_amount_with_words,
)
from app.services.extraction.classifier import classify_document_text, DOCUMENT_CLASSES
from app.services.extraction.tabular_parser import parse_tabular_content, detect_column_mapping
from app.services.extraction.effective_value import get_effective_field_value, get_effective_fields_map
from app.models.document import Document, ExtractedField, DocumentAnnotation, DocumentVersion
from app.models.audit_case import AuditCase


# -------------------------------------------------------------
# 1. PARSER UTILS TESTS
# -------------------------------------------------------------

def test_parse_indian_amount():
    v1, _ = parse_indian_amount("1,50,000.00")
    assert v1 == Decimal("150000.00")

    v2, _ = parse_indian_amount("12,34,56,789.50")
    assert v2 == Decimal("123456789.50")

    v3, _ = parse_indian_amount("Rs. 4,500/-")
    assert v3 == Decimal("4500")

    v4, _ = parse_indian_amount("₹ 12,000")
    assert v4 == Decimal("12000")

    v5, _ = parse_indian_amount("INR 85,000.00")
    assert v5 == Decimal("85000.00")

    v6, meta6 = parse_indian_amount("-5,000.00")
    assert v6 == Decimal("-5000.00")
    assert meta6["is_negative"] is True

    v7, meta7 = parse_indian_amount("(12,000.00)")
    assert v7 == Decimal("-12000.00")
    assert meta7["is_negative"] is True

    v8, meta8 = parse_indian_amount("10,000.00 Dr")
    assert v8 == Decimal("-10000.00")
    assert meta8["is_debit"] is True

    v9, meta9 = parse_indian_amount("25,000.00 Cr")
    assert v9 == Decimal("25000.00")
    assert meta9["is_credit"] is True

    v10, _ = parse_indian_amount("NIL")
    assert v10 is None


def test_words_to_amount():
    assert words_to_indian_amount("Forty Five Thousand Only") == Decimal(45000)
    assert words_to_indian_amount("One Lakh Twenty Thousand") == Decimal(120000)
    assert words_to_indian_amount("Two Crores Fifty Lakhs") == Decimal(25000000)

    # Cross check
    res = cross_check_amount_with_words(Decimal(45000), "Forty Five Thousand Only")
    assert res["match"] is True
    assert res["discrepancy"] is False

    res_discrepancy = cross_check_amount_with_words(Decimal(50000), "Forty Five Thousand Only")
    assert res_discrepancy["match"] is False
    assert res_discrepancy["discrepancy"] is True


def test_parse_indian_date():
    d1 = parse_indian_date("15/08/2024")
    assert d1 is not None and d1.day == 15 and d1.month == 8 and d1.year == 2024

    d2 = parse_indian_date("15-08-2024")
    assert d2 is not None and d2.day == 15 and d2.month == 8 and d2.year == 2024

    d3 = parse_indian_date("15.08.2024")
    assert d3 is not None and d3.day == 15 and d3.month == 8 and d3.year == 2024

    d4 = parse_indian_date("12 Mar 2025")
    assert d4 is not None and d4.day == 12 and d4.month == 3 and d4.year == 2025

    d5 = parse_indian_date("2024-08-15")
    assert d5 is not None and d5.day == 15 and d5.month == 8 and d5.year == 2024

    assert parse_indian_date("32/01/2024") is None
    assert parse_indian_date("31/02/2024") is None
    assert parse_indian_date("not a date") is None


def test_format_validators():
    # GSTIN
    valid_gstin, msg = validate_gstin("29AAAAA0000A1ZY")
    assert valid_gstin is True

    invalid_gstin_format, _ = validate_gstin("29AAAA0000A1Z")
    assert invalid_gstin_format is False

    invalid_gstin_checksum, _ = validate_gstin("29AAAAA0000A1Z0")
    assert invalid_gstin_checksum is False

    # PAN
    ok_pan, _ = validate_pan("ABCDE1234F")
    assert ok_pan is True
    bad_pan1, _ = validate_pan("12345ABCDE")
    assert bad_pan1 is False
    bad_pan2, _ = validate_pan("ABCD12345F")
    assert bad_pan2 is False

    # IFSC
    ok_ifsc1, _ = validate_ifsc("SBIN0001234")
    assert ok_ifsc1 is True
    ok_ifsc2, _ = validate_ifsc("KARB0000123")
    assert ok_ifsc2 is True
    bad_ifsc1, _ = validate_ifsc("SBIN1234")
    assert bad_ifsc1 is False
    bad_ifsc2, _ = validate_ifsc("SBIN1001234")
    assert bad_ifsc2 is False


# -------------------------------------------------------------
# 2. DOCUMENT CLASSIFIER TESTS
# -------------------------------------------------------------

def test_classify_document():
    # 13 classes verified
    test_cases = [
        ("TAX INVOICE Original for Recipient GSTIN: 29AAAAA0000A1Z5 Total Amount: Rs 50,000", "Bill"),
        ("OFFICE OF EXECUTIVE ENGINEER WORK ORDER No: EE/PRED/2024/45 Date: 12/04/2024", "Work Order"),
        ("GOVERNMENT OF KARNATAKA ADMINISTRATIVE SANCTION ORDER FD/EXP/2024/89", "Sanction Order"),
        ("ZILLA PANCHAYAT PAYMENT VOUCHER Debit Head: MGNREGA Passed for payment", "Voucher"),
        ("INVITATION FOR TENDERS (IFT) E-Procurement Tender Notification No: 124", "Tender"),
        ("P.W.D. MEASUREMENT BOOK First and Final Bill recorded on page 14", "Measurement Book"),
        ("WORK COMPLETION CERTIFICATE This is to certify that work has been completed satisfactorily", "Completion Certificate"),
        ("FORM GFR 12-C FORM OF UTILIZATION CERTIFICATE Certified that out of Rs 50,00,000 grants sanctioned", "Utilization Certificate"),
        ("CASH BOOK OF GRAM PANCHAYAT Opening Balance Closing Balance Daily Cash", "Cash Book"),
        ("GENERAL LEDGER ACCOUNT Scheme Expenditure Ledger Account Posting", "Ledger"),
        ("STATE BANK OF INDIA STATEMENT OF ACCOUNT Account Number: 1234567890 Value Date", "Bank Statement"),
    ]

    for text, expected_type in test_cases:
        res = classify_document_text(text)
        assert res["document_type"] == expected_type, f"Expected {expected_type}, got {res['document_type']} for text: {text[:40]}"
        assert res["confidence"] >= 0.4

    # Kannada keywords
    kannada_voucher = "ಗ್ರಾಮ ಪಂಚಾಯತಿ ಪಾವತಿ ಚೀಟಿ (Payment Voucher) ಮೊತ್ತ: ರೂ. 15,000"
    kres = classify_document_text(kannada_voucher)
    assert kres["document_type"] == "Voucher"

    # Fallback to unknown when no keywords match
    unknown_res = classify_document_text("Some arbitrary random text with no statutory words whatsoever 123 456.")
    assert unknown_res["document_type"] == "Unknown"


# -------------------------------------------------------------
# 3. TABULAR PARSER TESTS
# -------------------------------------------------------------

def test_tabular_parser_csv():
    csv_content = b"Voucher No,Date,Particulars,Debit Amount,Credit Amount\n101,15/04/2024,Cement Purchase,15000.00,0.00\n102,18/04/2024,Steel Delivery,25000.00,0.00"
    parsed = parse_tabular_content(csv_content, "text/csv")
    assert len(parsed["headers"]) == 5
    assert "Voucher No" in parsed["headers"]
    assert parsed["total_rows"] == 2
    assert len(parsed["transactions"]) == 2

    mapping, conf = detect_column_mapping(parsed["headers"])
    assert mapping["reference"] == "Voucher No"
    assert mapping["date"] == "Date"
    assert mapping["description"] == "Particulars"
    assert mapping["debit"] == "Debit Amount"
    assert conf >= 0.7


# -------------------------------------------------------------
# 4. EFFECTIVE FIELD VALUE HELPER TESTS
# -------------------------------------------------------------

def test_effective_field_value_helper():
    f1 = ExtractedField(
        field_name="total_amount",
        extracted_value="10000.00",
        is_overridden=False,
    )
    assert get_effective_field_value(f1) == "10000.00"

    f1.is_overridden = True
    f1.corrected_value = "12500.00"
    f1.override_comment = "Verified with physical voucher"
    assert get_effective_field_value(f1) == "12500.00"

    f2 = ExtractedField(
        field_name="invoice_number",
        extracted_value="INV-2024-001",
        is_overridden=False,
    )
    fields_map = get_effective_fields_map([f1, f2])
    assert fields_map["total_amount"] == "12500.00"
    assert fields_map["invoice_number"] == "INV-2024-001"


# -------------------------------------------------------------
# 5. API INTEGRATION TESTS: CASES & DOCUMENTS
# -------------------------------------------------------------

def test_audit_cases_api(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}

    # 1. Create Case
    payload = {
        "title": "Zilla Panchayat Mandya Audit FY 2024-25",
        "district": "Mandya",
        "taluk": "Mandya",
        "gram_panchayat": "Keregodu",
        "financial_year": "2024-25",
        "scheme_name": "MGNREGA",
        "description": "Comprehensive annual financial and statutory compliance audit",
    }
    res = client.post("/api/cases", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    case_data = res.json()
    assert case_data["case_number"].startswith("SAI-2024-")
    assert case_data["title"] == payload["title"]
    case_id = case_data["id"]

    # 2. Get Case by ID
    res_get = client.get(f"/api/cases/{case_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["district"] == "Mandya"

    # 3. List Cases with filter
    res_list = client.get("/api/cases?district=Mandya&financial_year=2024-25", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert any(c["id"] == case_id for c in items)

    # 4. Update Case
    res_upd = client.put(f"/api/cases/{case_id}", json={"status": "in_progress"}, headers=headers)
    assert res_upd.status_code == 200
    assert res_upd.json()["status"] == "in_progress"


def test_document_upload_and_pipeline_api(client, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['senior_auditor']}"}

    # 1. Create Case first
    case_res = client.post("/api/cases", json={
        "title": "Mysuru Water Supply Audit 2024-25",
        "district": "Mysuru",
        "financial_year": "2024-25",
        "scheme_name": "Jal Jeevan Mission"
    }, headers=headers)
    assert case_res.status_code == 201
    case_id = case_res.json()["id"]

    # 2. Upload Document with sync_process=True
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT /F1 12 Tf 72 712 Td (TAX INVOICE 12345 Rs. 50,000) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000201 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n307\n%%EOF"

    files = {
        "file": ("test_invoice.pdf", test_pdf_content, "application/pdf")
    }
    data = {
        "case_id": case_id,
        "document_type": "Bill",
        "sync_process": "true"
    }

    upload_res = client.post("/api/documents/upload", files=files, data=data, headers=headers)
    assert upload_res.status_code == 201, upload_res.text
    doc_resp = upload_res.json()
    doc_id = doc_resp["id"]
    job_id = doc_resp["job_id"]
    assert doc_id is not None
    assert job_id is not None

    # 3. Check Job Polling endpoint
    job_res = client.get(f"/api/jobs/{job_id}", headers=headers)
    assert job_res.status_code == 200
    assert job_res.json()["job_type"] == "document_extraction"

    # 4. Check Duplicate Upload Handling (HTTP 409 Conflict)
    dup_res = client.post("/api/documents/upload", files=files, data=data, headers=headers)
    assert dup_res.status_code == 409
    dup_detail = dup_res.json()["detail"]
    assert dup_detail["code"] == "DUPLICATE_CHECKSUM"

    # 5. Add a field manually for testing override & revert
    add_f_res = client.post(f"/api/documents/{doc_id}/fields", json={
        "field_name": "total_amount",
        "extracted_value": "50000.00",
        "source_page": 1,
        "comment": "Initial verified amount"
    }, headers=headers)
    assert add_f_res.status_code == 200
    field_id = add_f_res.json()["field_id"]

    # 6. Override Field API
    override_payload = {
        "corrected_value": "55000.00",
        "comment": "Re-verified after manual bill inspection"
    }
    ov_res = client.post(f"/api/documents/{doc_id}/fields/{field_id}/override", json=override_payload, headers=headers)
    assert ov_res.status_code == 200, ov_res.text
    assert ov_res.json()["effective_value"] == "55000.00"
    assert ov_res.json()["is_overridden"] is True

    # 7. Revert Override API
    rev_res = client.post(f"/api/documents/{doc_id}/fields/{field_id}/revert", headers=headers)
    assert rev_res.status_code == 200
    assert rev_res.json()["is_overridden"] is False

    # 8. Document Reclassification API
    reclass_res = client.post(f"/api/documents/{doc_id}/reclassify", json={
        "document_type": "Voucher",
        "comment": "Corrected by senior auditor"
    }, headers=headers)
    assert reclass_res.status_code == 200
    assert reclass_res.json()["document_type"] == "Voucher"

    # 9. Annotations API
    ann_payload = {
        "page": 1,
        "bbox": "[0.15, 0.25, 0.45, 0.35]",
        "note": "Discrepancy noted in vendor address"
    }
    ann_res = client.post(f"/api/documents/{doc_id}/annotations", json=ann_payload, headers=headers)
    assert ann_res.status_code == 200
    ann_id = ann_res.json()["id"]

    # 10. Document detail with annotations & fields
    doc_detail_res = client.get(f"/api/documents/{doc_id}", headers=headers)
    assert doc_detail_res.status_code == 200
    detail = doc_detail_res.json()
    assert len(detail["annotations"]) >= 1
    assert any(a["id"] == ann_id for a in detail["annotations"])

    # 11. Delete Annotation
    del_ann_res = client.delete(f"/api/documents/{doc_id}/annotations/{ann_id}", headers=headers)
    assert del_ann_res.status_code == 200

    # 12. Download endpoint
    dl_res = client.get(f"/api/documents/{doc_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
