import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.audit_case import AuditCase
from app.models.document import Document, ExtractedField
from app.models.financial import FinancialRecord, RecordLink, Transaction, Vendor, VendorAlias
from app.models.finding import Finding
from app.models.system import Holiday, MandatoryDocumentChecklist
from app.models.user import Department, Role, User
from app.services.verification.runner import run_case_verification


def generate_simple_pdf(filepath: str, title: str, lines: list[str]) -> int:
    """Generates a real PDF file using ReportLab and returns file size in bytes."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, title)
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Government of Karnataka - Rural Development & Panchayat Raj Department")
    c.setLineWidth(1)
    c.line(50, 725, 550, 725)
    
    y = 700
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(50, y, line)
        y -= 22
        if y < 50:
            c.showPage()
            y = 750
    c.save()
    return os.path.getsize(filepath)


def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def seed_verification_fixtures(db: Session = None) -> Dict[str, Any]:
    """Creates CAS-2024-MYS-002 (with 13 intentional anomalies)

    and CAS-2024-MYS-003 (clean benchmark case with 0 High/Critical findings).
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        print("[FIXTURES] Seeding Phase 3 Verification Fixture Cases...")

        # 1. Setup User and Department
        dept = db.query(Department).filter(Department.code == "ZP_MYS").first()
        if not dept:
            dept = Department(code="ZP_MYS", name="Mysuru Zilla Panchayat", type="Zilla Panchayat", district="Mysuru")
            db.add(dept)
            db.commit()
            db.refresh(dept)

        auditor = db.query(User).filter(User.email == "senior.auditor@stateaudit.kar.gov.in").first()
        if not auditor:
            role = db.query(Role).filter(Role.code == "senior_auditor").first()
            auditor = User(
                email="senior.auditor@stateaudit.kar.gov.in",
                hashed_password="dummy",
                full_name="Vidya Hegde (Senior Auditor)",
                role_id=role.id if role else "r1",
                department_id=dept.id,
                is_active=True
            )
            db.add(auditor)
            db.commit()
            db.refresh(auditor)

        # 2. Seed Mandatory Checklists
        checklists = [
            ("MGNREGA", "Measurement Book", True, "Mandatory measurement book recording site measurements"),
            ("MGNREGA", "Completion Certificate", True, "Executive engineer physical completion certificate"),
            ("Swachh Bharat Mission (Gramin)", "Bill", True, "Supplier statutory tax invoice"),
        ]
        for scheme, dtype, is_m, desc in checklists:
            ch = db.query(MandatoryDocumentChecklist).filter(
                MandatoryDocumentChecklist.scheme_name == scheme,
                MandatoryDocumentChecklist.document_type == dtype,
                MandatoryDocumentChecklist.deleted_at.is_(None)
            ).first()
            if not ch:
                ch = MandatoryDocumentChecklist(scheme_name=scheme, document_type=dtype, is_mandatory=is_m, description=desc)
                db.add(ch)
        db.commit()

        # 3. Seed Karnataka Public Holidays
        holidays = [
            (date(2024, 11, 1), "Kannada Rajyotsava", "Karnataka"),
            (date(2024, 4, 9), "Ugadi", "Karnataka"),
            (date(2024, 5, 1), "Labour Day", "Karnataka"),
            (date(2024, 8, 15), "Independence Day", "Karnataka"),
            (date(2024, 10, 2), "Gandhi Jayanti", "Karnataka"),
        ]
        for hdate, hname, hst in holidays:
            h = db.query(Holiday).filter(Holiday.holiday_date == hdate, Holiday.deleted_at.is_(None)).first()
            if not h:
                h = Holiday(holiday_date=hdate, name=hname, state=hst)
                db.add(h)
        db.commit()

        # 4. Helper for Vendors
        def get_or_create_vendor(name: str, gstin: str, pan: str, is_flagged: bool = False) -> Vendor:
            v = db.query(Vendor).filter(Vendor.legal_name == name).first()
            if not v:
                v = Vendor(legal_name=name, gstn=gstin, pan=pan, is_flagged=is_flagged)
                db.add(v)
                db.commit()
                db.refresh(v)
            return v

        v_cauvery = get_or_create_vendor("Cauvery Infra Projects", "29AABCC1234F1Z5", "AABCC1234F")
        v_chamundi = get_or_create_vendor("Chamundi Electricals & Spares", "29AABCE5678H1Z8", "AABCE5678H")
        v_borewell = get_or_create_vendor("Mysuru Borewell Services", "29AABCM9101J1Z2", "AABCM9101J")
        v_nandi = get_or_create_vendor("Nandi Construction Materials", "29AABCN2345K1Z6", "AABCN2345K")
        v_kril = get_or_create_vendor("Karnataka Rural Infra Ltd", "29AABCK6789L1Z9", "AABCK6789L")
        v_hassan = get_or_create_vendor("Hassan Tech Supplies", "29AABCH0123M1Z3", "AABCH0123M")

        storage_dir = os.path.join(settings.STORAGE_DIR, "fixtures")
        os.makedirs(storage_dir, exist_ok=True)

        # ==============================================================================
        # 5. BUILD CASE CAS-2024-MYS-002 (With 13 Intentional Anomalies)
        # ==============================================================================
        case_002 = db.query(AuditCase).filter(AuditCase.case_number == "CAS-2024-MYS-002").first()
        if not case_002:
            case_002 = AuditCase(
                case_number="CAS-2024-MYS-002",
                title="Zilla Panchayat Engineering Division Infrastructure Audit FY 2023-24 (Verification Benchmark)",
                financial_year="2023-24",
                department_id=dept.id,
                lead_auditor_id=auditor.id,
                scheme_name="MGNREGA",
                status="in_progress",
                risk_level="high",
                scope_notes="MGNREGA rural road construction and water works with intentional statutory compliance anomalies."
            )
            db.add(case_002)
            db.commit()
            db.refresh(case_002)
        else:
            case_002.scheme_name = "MGNREGA"
            db.commit()

        # Clear existing records for case 002 to ensure clean idempotency
        db.query(RecordLink).filter(RecordLink.case_id == case_002.id).delete(synchronize_session=False)
        for f in db.query(Finding).filter(Finding.case_id == case_002.id).all():
            db.delete(f)
        db.query(FinancialRecord).filter(FinancialRecord.case_id == case_002.id).delete(synchronize_session=False)
        for d in db.query(Document).filter(Document.case_id == case_002.id).all():
            db.delete(d)
        for t in db.query(Transaction).filter(Transaction.case_id == case_002.id).all():
            db.delete(t)
        db.commit()

        def add_doc_with_fields(case_id: str, title: str, filename: str, doc_type: str, fields: Dict[str, str], lines: list[str]) -> Document:
            pdf_path = os.path.join(storage_dir, filename)
            f_size = generate_simple_pdf(pdf_path, title, lines)
            sha = compute_file_sha256(pdf_path)

            doc = Document(
                case_id=case_id,
                title=title,
                original_filename=filename,
                stored_filename=filename,
                file_size=f_size,
                mime_type="application/pdf",
                sha256_hash=sha,
                document_type=doc_type,
                status="processed",
                page_count=1,
                uploader_id=auditor.id
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            for fname, val in fields.items():
                ef = ExtractedField(
                    document_id=doc.id,
                    field_name=fname,
                    extracted_value=str(val),
                    original_text=str(val),
                    confidence=1.0,
                    source_page=1,
                    validation_status="valid"
                )
                db.add(ef)
            db.commit()
            return doc

        # --- Document: Administrative Sanction AS-MGNREGA-2023-44 (₹10,00,000) ---
        add_doc_with_fields(
            case_id=case_002.id,
            title="Administrative Sanction Order AS-MGNREGA-2023-44",
            filename="AS-MGNREGA-2023-44.pdf",
            doc_type="Sanction Order",
            fields={
                "sanction_number": "AS-MGNREGA-2023-44",
                "sanction_date": "10-01-2024",
                "sanctioned_amount": "10,00,000.00",
                "scheme_name": "MGNREGA",
                "department": "Mysuru ZP Engineering Division"
            },
            lines=[
                "Sanction Number: AS-MGNREGA-2023-44",
                "Date: 10/01/2024",
                "Scheme: MGNREGA",
                "Sanctioned Ceiling Amount: Rs. 10,00,000.00 (Ten Lakhs Only)",
                "Work: Rural road gravelling and drainage culvert at Hunsur Taluk"
            ]
        )

        # --- Document: Work Order WO-2024-031 (₹12,40,000) ---
        # ANOMALY 9 (R-009): Work order dated 2024-02-15, but linked bill is dated 2024-02-01!
        add_doc_with_fields(
            case_id=case_002.id,
            title="Work Order WO-2024-031",
            filename="WO-2024-031.pdf",
            doc_type="Work Order",
            fields={
                "work_order_number": "WO-2024-031",
                "order_date": "15-02-2024",
                "contract_value": "12,40,000.00",
                "vendor_name": "Karnataka Rural Infra Ltd"
            },
            lines=[
                "Work Order No: WO-2024-031",
                "Date of Issue: 15/02/2024",
                "Contractor: Karnataka Rural Infra Ltd",
                "Contract Value: Rs. 12,40,000.00",
                "Terms: Standard KTPP Schedule"
            ]
        )

        # --- Document: Bill INV-2024-650 (Ante-dated before Work Order) ---
        # ANOMALY 9 (R-009): Dated 2024-02-01 (14 days before WO-2024-031!)
        # Contributes to ANOMALY 4 (R-004) cumulative payment exceeding sanction
        add_doc_with_fields(
            case_id=case_002.id,
            title="Tax Invoice INV-2024-650",
            filename="INV-2024-650.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-650",
                "bill_date": "01-02-2024",
                "total_amount": "5,00,000.00",
                "taxable_amount": "4,23,728.81",
                "tax_amount": "76,271.19",
                "vendor_name": "Karnataka Rural Infra Ltd",
                "gstin": "29AABCK6789L1Z9"
            },
            lines=[
                "Tax Invoice: INV-2024-650",
                "Invoice Date: 01/02/2024",
                "Supplier: Karnataka Rural Infra Ltd (GSTIN: 29AABCK6789L1Z9)",
                "Subtotal: Rs. 4,23,728.81",
                "GST (18%): Rs. 76,271.19",
                "Total Payable: Rs. 5,00,000.00"
            ]
        )

        # --- Document: Bill INV-2024-651 (Part 2 of WO-2024-031) ---
        # Contributes to ANOMALY 4 (R-004): cumulative payments 5L + 4.5L + 2.9L = 12.4L > 10L
        add_doc_with_fields(
            case_id=case_002.id,
            title="Tax Invoice INV-2024-651",
            filename="INV-2024-651.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-651",
                "bill_date": "25-02-2024",
                "total_amount": "4,50,000.00",
                "taxable_amount": "3,81,355.93",
                "tax_amount": "68,644.07",
                "vendor_name": "Karnataka Rural Infra Ltd",
                "gstin": "29AABCK6789L1Z9"
            },
            lines=[
                "Tax Invoice: INV-2024-651",
                "Invoice Date: 25/02/2024",
                "Supplier: Karnataka Rural Infra Ltd",
                "Total Amount: Rs. 4,50,000.00"
            ]
        )

        # --- Document: Bill INV-2024-652 (Part 3 of WO-2024-031) ---
        add_doc_with_fields(
            case_id=case_002.id,
            title="Tax Invoice INV-2024-652",
            filename="INV-2024-652.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-652",
                "bill_date": "10-03-2024",
                "total_amount": "2,90,000.00",
                "taxable_amount": "2,45,762.71",
                "tax_amount": "44,237.29",
                "vendor_name": "Karnataka Rural Infra Ltd",
                "gstin": "29AABCK6789L1Z9"
            },
            lines=[
                "Tax Invoice: INV-2024-652",
                "Invoice Date: 10/03/2024",
                "Supplier: Karnataka Rural Infra Ltd",
                "Total Amount: Rs. 2,90,000.00"
            ]
        )

        # --- ANOMALY 2 (R-002): Duplicate Invoice Number INV-2024-781 ---
        # Bill A from Chamundi Electricals
        add_doc_with_fields(
            case_id=case_002.id,
            title="Invoice INV-2024-781 (Batch A)",
            filename="INV-2024-781-A.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-781",
                "bill_date": "10-02-2024",
                "total_amount": "4,20,000.00",
                "vendor_name": "Chamundi Electricals & Spares",
                "gstin": "29AABCE5678H1Z8"
            },
            lines=[
                "Invoice No: INV-2024-781",
                "Date: 10/02/2024",
                "Supplier: Chamundi Electricals & Spares",
                "Amount: Rs. 4,20,000.00",
                "Supply: Distribution transformers and conductors"
            ]
        )

        # Bill B: Exact same invoice number INV-2024-781 re-submitted on 28-02-2024
        add_doc_with_fields(
            case_id=case_002.id,
            title="Invoice INV-2024-781 (Duplicate Submission)",
            filename="INV-2024-781-B.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-781",
                "bill_date": "28-02-2024",
                "total_amount": "4,20,000.00",
                "vendor_name": "Chamundi Electricals & Spares",
                "gstin": "29AABCE5678H1Z8"
            },
            lines=[
                "Invoice No: INV-2024-781",
                "Date: 28/02/2024",
                "Supplier: Chamundi Electricals & Spares",
                "Amount: Rs. 4,20,000.00"
            ]
        )

        # --- ANOMALY 3 (R-003): Amount Mismatch Between Bill & Voucher ---
        # Bill INV-2024-812 is ₹3,50,000.00
        add_doc_with_fields(
            case_id=case_002.id,
            title="Tax Invoice INV-2024-812",
            filename="INV-2024-812.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-812",
                "bill_date": "05-03-2024",
                "total_amount": "3,50,000.00",
                "vendor_name": "Mysuru Borewell Services",
                "gstin": "29AABCM9101J1Z2"
            },
            lines=[
                "Tax Invoice: INV-2024-812",
                "Date: 05/03/2024",
                "Supplier: Mysuru Borewell Services",
                "Total Amount: Rs. 3,50,000.00"
            ]
        )
        # But Voucher VOUCH-2024-102 passes payment for ₹3,85,000.00 (₹35,000 excess!)
        add_doc_with_fields(
            case_id=case_002.id,
            title="Payment Voucher VOUCH-2024-102",
            filename="VOUCH-2024-102.pdf",
            doc_type="Payment Voucher",
            fields={
                "voucher_number": "VOUCH-2024-102",
                "voucher_date": "08-03-2024",
                "total_amount": "3,85,000.00",
                "payment_reference": "INV-2024-812",
                "vendor_name": "Mysuru Borewell Services"
            },
            lines=[
                "Payment Voucher: VOUCH-2024-102",
                "Date: 08/03/2024",
                "Paid to: Mysuru Borewell Services",
                "Against Bill Ref: INV-2024-812",
                "Amount Passed: Rs. 3,85,000.00"
            ]
        )

        # --- ANOMALY 6 (R-006): Tax Anomaly (Invalid GST Rate & Calculation) ---
        # Bill INV-2024-905 has base ₹1,00,000, but tax ₹25,000 (25% rate - not a valid statutory slab!)
        add_doc_with_fields(
            case_id=case_002.id,
            title="Tax Invoice INV-2024-905",
            filename="INV-2024-905.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-905",
                "bill_date": "14-03-2024",
                "total_amount": "1,25,000.00",
                "taxable_amount": "1,00,000.00",
                "tax_amount": "25,000.00",
                "vendor_name": "Nandi Construction Materials",
                "gstin": "29AABCN2345K1Z6"
            },
            lines=[
                "Tax Invoice: INV-2024-905",
                "Date: 14/03/2024",
                "Supplier: Nandi Construction Materials",
                "Taxable Base Amount: Rs. 1,00,000.00",
                "GST Claimed: Rs. 25,000.00 (25% invalid tariff)",
                "Total Amount: Rs. 1,25,000.00"
            ]
        )

        # --- ANOMALY 7 (R-007): Arithmetic & Words Discrepancy ---
        # Base ₹2,00,000 + Tax ₹36,000 != Total ₹2,50,000, and words say "Two Lakh Thirty Six Thousand"
        add_doc_with_fields(
            case_id=case_002.id,
            title="Tax Invoice INV-2024-940",
            filename="INV-2024-940.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-940",
                "bill_date": "18-03-2024",
                "total_amount": "2,50,000.00",
                "taxable_amount": "2,00,000.00",
                "tax_amount": "36,000.00",
                "amount_in_words": "Rupees Two Lakh Thirty Six Thousand Only",
                "vendor_name": "Nandi Construction Materials",
                "gstin": "29AABCN2345K1Z6"
            },
            lines=[
                "Tax Invoice: INV-2024-940",
                "Date: 18/03/2024",
                "Supplier: Nandi Construction Materials",
                "Base Amount: Rs. 2,00,000.00",
                "GST (18%): Rs. 36,000.00",
                "Total Payable: Rs. 2,50,000.00",
                "Amount in Words: Rupees Two Lakh Thirty Six Thousand Only"
            ]
        )

        # --- Case 002 Transactions (Table / Ledger / Bank Feed) ---
        # ANOMALY 1 (R-001): Exact Duplicate Payment:
        # Same vendor (Cauvery Infra Projects), same amount (₹1,85,000.00), same date (2024-03-12), different vouchers!
        tx1 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-089",
            transaction_date=date(2024, 3, 12),
            amount=Decimal("185000.00"),
            debit=Decimal("185000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            payment_mode="Bank",
            description="Payment to Cauvery Infra Projects for culvert supply"
        )
        tx2 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-094",
            transaction_date=date(2024, 3, 12),
            amount=Decimal("185000.00"),
            debit=Decimal("185000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            payment_mode="Bank",
            description="Duplicate disbursement to Cauvery Infra Projects"
        )
        db.add_all([tx1, tx2])

        # ANOMALY 5 (R-005): Unbacked Bank Debit without matching bill or voucher
        tx_bank_unbacked = Transaction(
            case_id=case_002.id,
            voucher_no="DEBIT-2024-9901",
            transaction_date=date(2024, 3, 25),
            amount=Decimal("550000.00"),
            debit=Decimal("550000.00"),
            scheme_name="MGNREGA",
            payment_mode="Bank",
            description="Direct RTGS Bank debit without corresponding voucher or bill"
        )
        db.add(tx_bank_unbacked)

        # ANOMALY 10 (R-010): Voucher Sequence Inversion & Gap
        # VOUCH-2024-110 dated 2024-03-20, then VOUCH-2024-111 dated 2024-03-10 (date inversion!)
        # then jump to VOUCH-2024-125 (gap of 14 numbers)
        tx_seq1 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-110",
            transaction_date=date(2024, 3, 20),
            amount=Decimal("120000.00"),
            debit=Decimal("120000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            description="Voucher 110"
        )
        tx_seq2 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-111",
            transaction_date=date(2024, 3, 10),  # Chronological inversion!
            amount=Decimal("115000.00"),
            debit=Decimal("115000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            description="Voucher 111 ante-dated"
        )
        tx_seq3 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-125",  # Gap: 112 to 124 missing
            transaction_date=date(2024, 3, 22),
            amount=Decimal("95000.00"),
            debit=Decimal("95000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            description="Voucher 125 after gap"
        )
        db.add_all([tx_seq1, tx_seq2, tx_seq3])

        # ANOMALY 12 (R-014): Split Payments / Smurfing under ₹5,00,000 KTPP Tender Limit
        # 3 vouchers issued to Hassan Tech Supplies within 3 days: ₹4,95,000, ₹4,90,000, ₹4,85,000
        tx_split1 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-131",
            transaction_date=date(2024, 3, 15),
            amount=Decimal("495000.00"),
            debit=Decimal("495000.00"),
            vendor_id=v_hassan.id,
            scheme_name="MGNREGA",
            description="Split purchase payment 1 of 3 to Hassan Tech"
        )
        tx_split2 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-132",
            transaction_date=date(2024, 3, 16),
            amount=Decimal("490000.00"),
            debit=Decimal("490000.00"),
            vendor_id=v_hassan.id,
            scheme_name="MGNREGA",
            description="Split purchase payment 2 of 3 to Hassan Tech"
        )
        tx_split3 = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-133",
            transaction_date=date(2024, 3, 17),
            amount=Decimal("485000.00"),
            debit=Decimal("485000.00"),
            vendor_id=v_hassan.id,
            scheme_name="MGNREGA",
            description="Split purchase payment 3 of 3 to Hassan Tech"
        )
        db.add_all([tx_split1, tx_split2, tx_split3])

        # ANOMALY 13 (R-016): Unusual Timing:
        # A) Voucher on Sunday March 31, 2024 (Last day of FY year-end rush)
        tx_timing_sunday = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-140",
            transaction_date=date(2024, 3, 31),
            amount=Decimal("350000.00"),
            debit=Decimal("350000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            description="Fiscal year-end rush payment on Sunday 31-March-2024"
        )
        # B) Voucher on Kannada Rajyotsava (Karnataka Public Holiday Nov 1, 2024)
        tx_timing_holiday = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-141",
            transaction_date=date(2024, 11, 1),
            amount=Decimal("220000.00"),
            debit=Decimal("220000.00"),
            vendor_id=v_cauvery.id,
            scheme_name="MGNREGA",
            description="Disbursement processed on state public holiday Kannada Rajyotsava"
        )
        db.add_all([tx_timing_sunday, tx_timing_holiday])

        # ANOMALY 11 (R-011): Vendor Concentration:
        # Large disbursements to Karnataka Rural Infra Ltd pushing its concentration share > 50%
        tx_conc = Transaction(
            case_id=case_002.id,
            voucher_no="VOUCH-2024-150",
            transaction_date=date(2024, 3, 26),
            amount=Decimal("2500000.00"),
            debit=Decimal("2500000.00"),
            vendor_id=v_kril.id,
            scheme_name="MGNREGA",
            description="Major infrastructure tranche to Karnataka Rural Infra Ltd"
        )
        db.add(tx_conc)
        db.commit()

        # ==============================================================================
        # 6. BUILD CLEAN CASE CAS-2024-MYS-003 (0 High/Critical Findings)
        # ==============================================================================
        case_003 = db.query(AuditCase).filter(AuditCase.case_number == "CAS-2024-MYS-003").first()
        if not case_003:
            case_003 = AuditCase(
                case_number="CAS-2024-MYS-003",
                title="Gram Panchayat Sanitation & School Infrastructure Phase II (Clean Benchmark Case)",
                financial_year="2023-24",
                department_id=dept.id,
                lead_auditor_id=auditor.id,
                scheme_name="Swachh Bharat Mission (Gramin)",
                status="in_progress",
                risk_level="low",
                scope_notes="Swachh Bharat Mission rural sanitation works with clean statutory compliance."
            )
            db.add(case_003)
            db.commit()
            db.refresh(case_003)
        else:
            case_003.scheme_name = "Swachh Bharat Mission (Gramin)"
            db.commit()

        # Clear existing records for case 003
        db.query(RecordLink).filter(RecordLink.case_id == case_003.id).delete(synchronize_session=False)
        for f in db.query(Finding).filter(Finding.case_id == case_003.id).all():
            db.delete(f)
        db.query(FinancialRecord).filter(FinancialRecord.case_id == case_003.id).delete(synchronize_session=False)
        for d in db.query(Document).filter(Document.case_id == case_003.id).all():
            db.delete(d)
        for t in db.query(Transaction).filter(Transaction.case_id == case_003.id).all():
            db.delete(t)
        db.commit()

        v_eco = get_or_create_vendor("Mysuru Eco Sanitations", "29AABCE1122D1Z4", "AABCE1122D")
        v_water = get_or_create_vendor("Cauvery Water Systems", "29AABCW3344E1Z7", "AABCW3344E")
        v_solar = get_or_create_vendor("Chamundi Solar Solutions", "29AABCS5566K1Z1", "AABCS5566K")

        # Clean Sanction: ₹10,00,000.00
        add_doc_with_fields(
            case_id=case_003.id,
            title="Administrative Sanction AS-SBM-2023-10",
            filename="AS-SBM-2023-10.pdf",
            doc_type="Sanction Order",
            fields={
                "sanction_number": "AS-SBM-2023-10",
                "sanction_date": "15-10-2023",
                "sanctioned_amount": "10,00,000.00",
                "scheme_name": "Swachh Bharat Mission (Gramin)"
            },
            lines=[
                "Sanction: AS-SBM-2023-10",
                "Date: 15/10/2023",
                "Sanctioned Amount: Rs. 10,00,000.00"
            ]
        )

        # Clean Work Order 1: ₹3,00,000.00 on 2023-11-10 to Mysuru Eco
        add_doc_with_fields(
            case_id=case_003.id,
            title="Work Order WO-2023-088",
            filename="WO-2023-088.pdf",
            doc_type="Work Order",
            fields={
                "work_order_number": "WO-2023-088",
                "order_date": "10-11-2023",
                "contract_value": "3,00,000.00",
                "vendor_name": "Mysuru Eco Sanitations"
            },
            lines=[
                "Work Order: WO-2023-088",
                "Date: 10/11/2023",
                "Contractor: Mysuru Eco Sanitations",
                "Value: Rs. 3,00,000.00"
            ]
        )

        # Clean Bill 1: ₹3,00,000.00 on 2023-11-25 (after Work Order, valid 18% GST, words match)
        add_doc_with_fields(
            case_id=case_003.id,
            title="Tax Invoice INV-2023-412",
            filename="INV-2023-412.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2023-412",
                "bill_date": "25-11-2023",
                "total_amount": "3,00,000.00",
                "taxable_amount": "2,54,237.29",
                "tax_amount": "45,762.71",
                "amount_in_words": "Rupees Three Lakh Only",
                "vendor_name": "Mysuru Eco Sanitations",
                "gstin": "29AABCE1122D1Z4"
            },
            lines=[
                "Invoice: INV-2023-412",
                "Date: 25/11/2023",
                "Supplier: Mysuru Eco Sanitations",
                "Taxable: Rs. 2,54,237.29",
                "GST (18%): Rs. 45,762.71",
                "Total: Rs. 3,00,000.00",
                "Words: Rupees Three Lakh Only"
            ]
        )

        # Clean Voucher 1 & Bank Debit: Matching amount ₹3,00,000 on weekday
        tx_clean1 = Transaction(
            case_id=case_003.id,
            voucher_no="VOUCH-2023-045",
            transaction_date=date(2023, 11, 28),  # Tuesday (weekday, non-holiday)
            amount=Decimal("300000.00"),
            debit=Decimal("300000.00"),
            vendor_id=v_eco.id,
            scheme_name="Swachh Bharat Mission (Gramin)",
            payment_mode="Bank",
            description="Payment against Bill INV-2023-412 to Mysuru Eco Sanitations"
        )
        tx_clean_bank1 = Transaction(
            case_id=case_003.id,
            voucher_no="DEBIT-2023-5511",
            transaction_date=date(2023, 11, 29),
            amount=Decimal("300000.00"),
            debit=Decimal("300000.00"),
            vendor_id=v_eco.id,
            scheme_name="Swachh Bharat Mission (Gramin)",
            payment_mode="Bank",
            description="Bank RTGS debit matching VOUCH-2023-045"
        )

        # Clean Work Order 2: ₹3,00,000.00 on 2023-12-05 to Cauvery Water Systems
        add_doc_with_fields(
            case_id=case_003.id,
            title="Work Order WO-2023-095",
            filename="WO-2023-095.pdf",
            doc_type="Work Order",
            fields={
                "work_order_number": "WO-2023-095",
                "order_date": "05-12-2023",
                "contract_value": "3,00,000.00",
                "vendor_name": "Cauvery Water Systems"
            },
            lines=[
                "Work Order: WO-2023-095",
                "Date: 05/12/2023",
                "Contractor: Cauvery Water Systems",
                "Value: Rs. 3,00,000.00"
            ]
        )

        # Clean Bill 2: ₹3,00,000.00 on 2023-12-15
        add_doc_with_fields(
            case_id=case_003.id,
            title="Tax Invoice INV-2023-440",
            filename="INV-2023-440.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2023-440",
                "bill_date": "15-12-2023",
                "total_amount": "3,00,000.00",
                "taxable_amount": "2,54,237.29",
                "tax_amount": "45,762.71",
                "amount_in_words": "Rupees Three Lakh Only",
                "vendor_name": "Cauvery Water Systems",
                "gstin": "29AABCW3344E1Z7"
            },
            lines=[
                "Invoice: INV-2023-440",
                "Date: 15/12/2023",
                "Supplier: Cauvery Water Systems",
                "Taxable: Rs. 2,54,237.29",
                "GST (18%): Rs. 45,762.71",
                "Total: Rs. 3,00,000.00",
                "Words: Rupees Three Lakh Only"
            ]
        )

        # Clean Voucher 2 & Bank Debit: ₹3,00,000 on sequential voucher number 046
        tx_clean2 = Transaction(
            case_id=case_003.id,
            voucher_no="VOUCH-2023-046",
            transaction_date=date(2023, 12, 18),  # Monday (weekday, consecutive number)
            amount=Decimal("300000.00"),
            debit=Decimal("300000.00"),
            vendor_id=v_water.id,
            scheme_name="Swachh Bharat Mission (Gramin)",
            payment_mode="Bank",
            description="Payment against Bill INV-2023-440 to Cauvery Water Systems"
        )
        tx_clean_bank2 = Transaction(
            case_id=case_003.id,
            voucher_no="DEBIT-2023-5520",
            transaction_date=date(2023, 12, 19),
            amount=Decimal("300000.00"),
            debit=Decimal("300000.00"),
            vendor_id=v_water.id,
            scheme_name="Swachh Bharat Mission (Gramin)",
            payment_mode="Bank",
            description="Bank RTGS debit matching VOUCH-2023-046"
        )

        # Clean Work Order 3: ₹2,00,000.00 on 2024-01-08 to Chamundi Solar Solutions
        add_doc_with_fields(
            case_id=case_003.id,
            title="Work Order WO-2024-002",
            filename="WO-2024-002.pdf",
            doc_type="Work Order",
            fields={
                "work_order_number": "WO-2024-002",
                "order_date": "08-01-2024",
                "contract_value": "2,00,000.00",
                "vendor_name": "Chamundi Solar Solutions"
            },
            lines=[
                "Work Order: WO-2024-002",
                "Date: 08/01/2024",
                "Contractor: Chamundi Solar Solutions",
                "Value: Rs. 2,00,000.00"
            ]
        )

        # Clean Bill 3: ₹2,00,000.00 on 2024-01-18
        add_doc_with_fields(
            case_id=case_003.id,
            title="Tax Invoice INV-2024-115",
            filename="INV-2024-115.pdf",
            doc_type="Tax Invoice / Bill",
            fields={
                "bill_number": "INV-2024-115",
                "bill_date": "18-01-2024",
                "total_amount": "2,00,000.00",
                "taxable_amount": "1,69,491.53",
                "tax_amount": "30,508.47",
                "amount_in_words": "Rupees Two Lakh Only",
                "vendor_name": "Chamundi Solar Solutions",
                "gstin": "29AABCS5566K1Z1"
            },
            lines=[
                "Invoice: INV-2024-115",
                "Date: 18/01/2024",
                "Supplier: Chamundi Solar Solutions",
                "Taxable: Rs. 1,69,491.53",
                "GST (18%): Rs. 30,508.47",
                "Total: Rs. 2,00,000.00",
                "Words: Rupees Two Lakh Only"
            ]
        )

        # Clean Voucher 3 & Bank Debit: ₹2,00,000 on sequential voucher number 047
        tx_clean3 = Transaction(
            case_id=case_003.id,
            voucher_no="VOUCH-2024-047",
            transaction_date=date(2024, 1, 22),  # Monday (weekday, consecutive number)
            amount=Decimal("200000.00"),
            debit=Decimal("200000.00"),
            vendor_id=v_solar.id,
            scheme_name="Swachh Bharat Mission (Gramin)",
            payment_mode="Bank",
            description="Payment against Bill INV-2024-115 to Chamundi Solar Solutions"
        )
        tx_clean_bank3 = Transaction(
            case_id=case_003.id,
            voucher_no="DEBIT-2024-5535",
            transaction_date=date(2024, 1, 23),
            amount=Decimal("200000.00"),
            debit=Decimal("200000.00"),
            vendor_id=v_solar.id,
            scheme_name="Swachh Bharat Mission (Gramin)",
            payment_mode="Bank",
            description="Bank RTGS debit matching VOUCH-2024-047"
        )

        db.add_all([tx_clean1, tx_clean_bank1, tx_clean2, tx_clean_bank2, tx_clean3, tx_clean_bank3])
        db.commit()

        # ==============================================================================
        # 7. EXECUTE VERIFICATION ENGINE FOR BOTH CASES
        # ==============================================================================
        print("[FIXTURES] Running verification engine for CAS-2024-MYS-002...")
        summary_002 = run_case_verification(db, case_002.id, triggered_by_id=auditor.id)

        print("[FIXTURES] Running verification engine for CAS-2024-MYS-003 (clean)...")
        summary_003 = run_case_verification(db, case_003.id, triggered_by_id=auditor.id)

        print(f"[OK] CAS-2024-MYS-002: {summary_002['findings_created']} findings generated. Score: {summary_002['case_risk_score']} ({summary_002['risk_band']})")
        print(f"[OK] CAS-2024-MYS-003: {summary_003['findings_created']} findings generated. Score: {summary_003['case_risk_score']} ({summary_003['risk_band']})")

        return {
            "case_002_id": case_002.id,
            "case_002_summary": summary_002,
            "case_003_id": case_003.id,
            "case_003_summary": summary_003
        }

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding verification fixtures failed: {e}")
        raise e
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_verification_fixtures()
