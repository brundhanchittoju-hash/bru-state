import os
import json
import csv
from decimal import Decimal
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

SEED_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_FILES_DIR = os.path.join(SEED_DIR, "sample_files")
GROUND_TRUTH_FILE = os.path.join(SEED_DIR, "ground_truth.json")


def ensure_dirs():
    os.makedirs(SAMPLE_FILES_DIR, exist_ok=True)


# ==============================================================================
# 1. Clean Tax Invoice (PDF)
# ==============================================================================
def create_clean_bill_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "TAX INVOICE - DEMO DATA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "State of Karnataka • Panchayati Raj Procurement")

    c.line(50, height - 75, width - 50, height - 75)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 100, "Vendor: M/s Cauvery Infratech Pvt Ltd")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 118, "GSTIN: 29AABCC1234D1Z7")
    c.drawString(50, height - 134, "PAN: AABCC1234D")
    c.drawString(50, height - 150, "Bank A/c: 987654321012")
    c.drawString(50, height - 166, "IFSC: SBIN0001234")

    c.drawString(350, height - 100, "Invoice No: INV-2024-089")
    c.drawString(350, height - 118, "Invoice Date: 14/05/2024")
    c.drawString(350, height - 134, "Department: Mysuru Zilla Panchayat")
    c.drawString(350, height - 150, "Project: Rural Drinking Water Pipeline Installation")

    c.line(50, height - 180, width - 50, height - 180)

    # Item line
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 200, "Description")
    c.drawString(350, height - 200, "Qty")
    c.drawString(450, height - 200, "Amount")
    c.line(50, height - 205, width - 50, height - 205)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 225, "HDPE Pipe 110mm Class 4 for Bilikere Taluk")
    c.drawString(350, height - 225, "1 Lot")
    c.drawString(450, height - 225, "Rs. 4,85,000.00")

    c.line(50, height - 240, width - 50, height - 240)

    # Tax & Total
    c.drawString(300, height - 260, "GST Rate: 18%")
    c.drawString(300, height - 278, "Total GST: Rs. 87,300.00")
    c.drawString(300, height - 296, "Total Tax: Rs. 87,300.00")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - 320, "Total Amount: Rs. 4,85,000.00")

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, height - 360, "Amount in Words: Rupees Four Lakh Eighty Five Thousand Only")

    c.setFont("Helvetica", 9)
    c.drawString(50, height - 420, "Certified that particulars given above are true and correct.")
    c.drawString(50, height - 440, "Authorized Signatory: S. Ramesh (Cauvery Infratech Pvt Ltd)")
    c.drawString(350, height - 440, "Passed for Payment by AEE Mysuru ZP")

    c.save()


# ==============================================================================
# 2. Deliberately Messy Bill (PDF)
# ==============================================================================
def create_messy_bill_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Courier-Bold", 14)
    c.drawString(60, height - 60, "COMMERCIAL CLAIM & BILL - DEMO DATA")
    c.setFont("Courier", 9)
    c.drawString(60, height - 80, "REF: MYS/ZP/SUPPLY/2024-25")

    c.line(60, height - 90, width - 60, height - 90)

    c.drawString(60, height - 110, "Supplier: Chamundi Electricals & Spares")
    c.drawString(60, height - 125, "Bill No: BL/MYS/99")
    c.drawString(60, height - 140, "Date: 12.03.2025")
    c.drawString(60, height - 155, "GST: 29AAAAA0000A1Z5")
    c.drawString(60, height - 170, "PAN: AAAAA0000A")
    c.drawString(60, height - 185, "IFSC: KARB0000123")
    c.drawString(60, height - 200, "A/c No: 1234567890123")

    c.drawString(60, height - 240, "SUPPLY PARTICULARS: Solar Street Light Batteries 12V 100AH")
    c.drawString(60, height - 270, "BILL / CLAIM: RS. 2,45,600/-")
    c.drawString(60, height - 300, "Rupees: Rupees Two Lakh Forty Five Thousand Six Hundred Only")

    c.save()


# ==============================================================================
# 3. Payment Voucher (PDF)
# ==============================================================================
def create_voucher_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, height - 50, "PAYMENT VOUCHER - DEMO DATA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Bilikere Gram Panchayat • Hunsur Taluk • Mysuru District")

    c.line(50, height - 75, width - 50, height - 75)

    c.drawString(50, height - 100, "Voucher No: VR-2024-0042")
    c.drawString(350, height - 100, "Date: 22/06/2024")
    c.drawString(50, height - 120, "Head of Account: MGNREGA Material Component")
    c.drawString(350, height - 120, "Cheque No: 542109")
    c.drawString(50, height - 140, "Payment Ref: UTR98234710298")

    c.drawString(50, height - 170, "Paid To: Karnataka Rural Infrastructure Development Ltd (KRIDL)")
    c.drawString(50, height - 190, "Particulars: Construction of Solid Waste Management Shed (Phase 1)")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 230, "Passed for Payment: Rs. 1,25,000.00")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, height - 250, "Amount in Words: Rupees One Lakh Twenty Five Thousand Only")

    c.drawString(50, height - 310, "Panchayat Development Officer (PDO)")
    c.drawString(350, height - 310, "President / Gram Panchayat")

    c.save()


# ==============================================================================
# 4. Work Order (PDF)
# ==============================================================================
def create_work_order_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "OFFICE OF THE EXECUTIVE ENGINEER, ZILLA PANCHAYAT MYSURU")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 70, "WORK ORDER / AWARD OF WORK - DEMO DATA")

    c.line(50, height - 78, width - 50, height - 78)

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 100, "Work Order No: WO/ZP/MYS/2024/77")
    c.drawString(350, height - 100, "Dated: 02/04/2024")
    c.drawString(50, height - 120, "Contractor: Sri Manjunatha Engineering Works")
    c.drawString(50, height - 140, "Name of Work: Rural Drinking Water Pipeline Installation Hunsur Taluk")
    c.drawString(50, height - 160, "Tender Premium: 4.5% Above Estimated Rate")
    c.drawString(50, height - 180, "Stipulated Date of Commencement: 10/04/2024")
    c.drawString(50, height - 200, "Stipulated Date of Completion: 30/09/2024")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 230, "Sanctioned Contract Amount: Rs. 14,50,000.00")

    c.save()


# ==============================================================================
# 5. Sanction Order (PDF)
# ==============================================================================
def create_sanction_order_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, height - 50, "PROCEEDINGS OF THE CHIEF EXECUTIVE OFFICER, ZILLA PANCHAYAT MYSURU")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "Sub: Administrative Sanction under 15th Finance Commission Grants")

    c.line(50, height - 78, width - 50, height - 78)

    c.drawString(50, height - 100, "Administrative Sanction No: AS/RDPR/15FC/2024/104")
    c.drawString(350, height - 100, "Date: 10/04/2024")
    c.drawString(50, height - 125, "Government Order: GO No. RDP/71/PRJ/2024")
    c.drawString(50, height - 150, "Grant in Aid: 15th Finance Commission Untied Grants")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 180, "Sanctioned Estimate: Rs. 25,00,000.00")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 210, "Sanction is hereby accorded for execution of basic water and sanitation amenities.")

    c.save()


# ==============================================================================
# 6. Tender Notice (PDF)
# ==============================================================================
def create_tender_notice_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "NOTICE INVITING TENDER (NIT) - DEMO DATA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Government of Karnataka • Karnataka e-Procurement Portal")

    c.line(50, height - 75, width - 50, height - 75)

    c.drawString(50, height - 100, "Tender Notification No: NIT/MYS/2024/T-18")
    c.drawString(350, height - 100, "Date: 15/01/2024")
    c.drawString(50, height - 125, "Project: Construction of Bridge Culvert at Bilikere Gram Panchayat")
    c.drawString(50, height - 150, "Estimated Cost: Rs. 18,20,000.00")
    c.drawString(50, height - 175, "Earnest Money Deposit (EMD): Rs. 36,400.00")
    c.drawString(50, height - 200, "Tender Document Fee: Rs. 2,000.00")

    c.save()


# ==============================================================================
# 7. Measurement Book Page (PDF)
# ==============================================================================
def create_measurement_book_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "MEASUREMENT BOOK (M-BOOK) - DEMO DATA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Public Works & Rural Engineering Services • Division Mysuru")

    c.line(50, height - 75, width - 50, height - 75)

    c.drawString(50, height - 100, "MB No: MB-741/2024")
    c.drawString(350, height - 100, "Date: 18/07/2024")
    c.drawString(50, height - 125, "Running Account Bill: RA Bill No 03")
    c.drawString(50, height - 150, "Items of Work: Earthwork Excavation & Concrete Base Chainage 0/000 to 1/250")
    c.drawString(50, height - 175, "Measurements Recorded by Junior Engineer, Verified by AEE")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 210, "Total Amount Passed: Rs. 3,15,400.00")

    c.save()


# ==============================================================================
# 8. Completion Certificate (PDF)
# ==============================================================================
def create_completion_cert_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "WORK COMPLETION CERTIFICATE - DEMO DATA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Zilla Panchayat Engineering Sub-Division Hunsur")

    c.line(50, height - 75, width - 50, height - 75)

    c.drawString(50, height - 100, "Work: Construction of PMAY-G Community Hall Nanjangud")
    c.drawString(50, height - 125, "Actual Date of Completion: 30/08/2024")
    c.drawString(50, height - 150, "Final Bill Amount: Rs. 8,90,000.00")
    c.drawString(50, height - 180, "Certified that the work has been satisfactorily completed in accordance with specifications.")

    c.save()


# ==============================================================================
# 9. Utilization Certificate (PDF)
# ==============================================================================
def create_utilization_cert_pdf(file_path: str):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "FORM GFR 12-C: UTILIZATION CERTIFICATE - DEMO DATA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "15th Finance Commission Untied Grants • Financial Year 2023-24")

    c.line(50, height - 75, width - 50, height - 75)

    c.drawString(50, height - 100, "Date: 31/03/2024")
    c.drawString(50, height - 125, "Grants-in-aid Sanctioned: Rs. 50,00,000.00")
    c.drawString(50, height - 150, "Certified that out of Rs. 50,00,000.00 of grants sanctioned, a sum of")
    c.drawString(50, height - 170, "Rs. 48,20,000.00 has been utilized for the purpose for which it was sanctioned.")
    c.drawString(50, height - 195, "Balance remaining unutilized: Rs. 1,80,000.00")

    c.save()


# ==============================================================================
# 10. Cash Book (XLSX)
# ==============================================================================
def create_cash_book_xlsx(file_path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cash Book 2024"

    headers = ["Date", "Particulars", "Voucher No", "Debit", "Credit", "Balance"]
    ws.append(headers)

    data = [
        ["01/04/2024", "Opening Cash Balance", "OB-01", "", "", "1,50,000.00"],
        ["12/04/2024", "MGNREGA Muster Roll Payment", "VR-01", "45,000.00", "", "1,05,000.00"],
        ["28/04/2024", "15th FC Grant Installment", "CR-12", "", "2,00,000.00", "3,05,000.00"],
        ["15/05/2024", "Cauvery Infratech HDPE Pipes", "VR-02", "1,85,000.00", "", "1,20,000.00"],
        ["31/05/2024", "Closing Cash Balance", "CB-01", "", "", "1,20,000.00"],
    ]
    for row in data:
        ws.append(row)

    wb.save(file_path)


# ==============================================================================
# 11. General Ledger (XLSX)
# ==============================================================================
def create_ledger_xlsx(file_path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "General Ledger"

    headers = ["Txn Date", "Account Head", "Ref No", "Dr Amount", "Cr Amount", "Net Balance"]
    ws.append(headers)

    data = [
        ["05/04/2024", "PMAY-G Housing Beneficiary Grants", "REF-801", "2,50,000.00", "", "2,50,000.00 Dr"],
        ["20/04/2024", "State Share Matching Grant", "REF-802", "", "5,00,000.00", "2,50,000.00 Cr"],
        ["14/05/2024", "Water Sanitation Pipeline Works", "REF-803", "4,85,000.00", "", "2,35,000.00 Dr"],
    ]
    for row in data:
        ws.append(row)

    wb.save(file_path)


# ==============================================================================
# 12. Bank Statement (CSV)
# ==============================================================================
def create_bank_statement_csv(file_path: str):
    headers = ["Value Date", "Description", "Ref / UTR", "Withdrawal Amt", "Deposit Amt", "Closing Balance"]
    rows = [
        ["02/04/2024", "B/F OPENING BALANCE", "SBI-001", "", "", "12,45,000.00"],
        ["15/04/2024", "NEFT-KRIDL CONTRACTOR PYMT", "UTR98234710298", "1,25,000.00", "", "11,20,000.00"],
        ["02/05/2024", "GOVT OF KARNATAKA TREASURY CHQ", "CHQ-778899", "", "10,00,000.00", "21,20,000.00"],
        ["18/05/2024", "RTGS-CAUVERY INFRATECH PVT LTD", "UTR99234810299", "4,85,000.00", "", "16,35,000.00"],
    ]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


# ==============================================================================
# 13. Scanned-style Image Pages (PNG via Pillow)
# ==============================================================================
def create_scanned_image(file_path: str, title: str, text_lines: list[str], rotate_deg: float = 1.0):
    img = Image.new("RGB", (800, 1000), color=(248, 248, 246))
    draw = ImageDraw.Draw(img)

    # Simple noise / texture
    draw.rectangle([20, 20, 780, 980], outline=(180, 180, 180), width=2)
    draw.text((50, 50), f"{title} - DEMO DATA", fill=(30, 30, 30))

    y = 100
    for line in text_lines:
        draw.text((50, y), line, fill=(50, 50, 50))
        y += 35

    # Rotate slightly to simulate scanned document
    rotated = img.rotate(rotate_deg, expand=False, fillcolor=(240, 240, 240))
    rotated.save(file_path)


def generate_all_samples():
    """Generates all 13 demo audit files and outputs ground_truth.json."""
    ensure_dirs()

    # 1. Clean Bill
    f1 = os.path.join(SAMPLE_FILES_DIR, "bill_clean.pdf")
    create_clean_bill_pdf(f1)

    # 2. Messy Bill
    f2 = os.path.join(SAMPLE_FILES_DIR, "bill_messy.pdf")
    create_messy_bill_pdf(f2)

    # 3. Voucher
    f3 = os.path.join(SAMPLE_FILES_DIR, "voucher_001.pdf")
    create_voucher_pdf(f3)

    # 4. Work Order
    f4 = os.path.join(SAMPLE_FILES_DIR, "work_order_001.pdf")
    create_work_order_pdf(f4)

    # 5. Sanction Order
    f5 = os.path.join(SAMPLE_FILES_DIR, "sanction_order_001.pdf")
    create_sanction_order_pdf(f5)

    # 6. Tender Notice
    f6 = os.path.join(SAMPLE_FILES_DIR, "tender_notice_001.pdf")
    create_tender_notice_pdf(f6)

    # 7. Measurement Book
    f7 = os.path.join(SAMPLE_FILES_DIR, "measurement_book_001.pdf")
    create_measurement_book_pdf(f7)

    # 8. Completion Certificate
    f8 = os.path.join(SAMPLE_FILES_DIR, "completion_cert_001.pdf")
    create_completion_cert_pdf(f8)

    # 9. Utilization Certificate
    f9 = os.path.join(SAMPLE_FILES_DIR, "utilization_cert_001.pdf")
    create_utilization_cert_pdf(f9)

    # 10. Cash Book
    f10 = os.path.join(SAMPLE_FILES_DIR, "cash_book_2024.xlsx")
    create_cash_book_xlsx(f10)

    # 11. General Ledger
    f11 = os.path.join(SAMPLE_FILES_DIR, "ledger_2024.xlsx")
    create_ledger_xlsx(f11)

    # 12. Bank Statement
    f12 = os.path.join(SAMPLE_FILES_DIR, "bank_statement_mysuru.csv")
    create_bank_statement_csv(f12)

    # 13. Scanned images
    f13_1 = os.path.join(SAMPLE_FILES_DIR, "scanned_voucher_p1.png")
    create_scanned_image(
        f13_1,
        "GRAM PANCHAYAT PAYMENT VOUCHER",
        [
            "Voucher No: VR-9901",
            "Date: 15/06/2024",
            "Payment To: KRIDL Mysuru",
            "Total Amount: Rs. 75,000/-",
            "Head: MGNREGA Earthwork",
        ],
        rotate_deg=1.2,
    )

    f13_2 = os.path.join(SAMPLE_FILES_DIR, "scanned_invoice_p2.png")
    create_scanned_image(
        f13_2,
        "TAX INVOICE - HARDWARE SUPPLIES",
        [
            "Invoice No: INV-MYS-554",
            "Invoice Date: 20/07/2024",
            "GSTIN: 29AABCC1234D1Z7",
            "Total Amount: Rs. 1,12,000/-",
        ],
        rotate_deg=-0.8,
    )

    f13_3 = os.path.join(SAMPLE_FILES_DIR, "scanned_receipt_p3.png")
    create_scanned_image(
        f13_3,
        "ACKNOWLEDGEMENT RECEIPT",
        [
            "Receipt No: RCT-2024-88",
            "Dated: 05/08/2024",
            "Received from Bilikere GP",
            "Amount: Rs. 15,000/-",
        ],
        rotate_deg=0.5,
    )

    # Ground Truth mapping for accuracy evaluation
    ground_truth = {
        "bill_clean.pdf": {
            "expected_type": "Bill",
            "key_fields": {
                "bill_number": "INV-2024-089",
                "invoice_date": "2024-05-14",
                "amount": "485000.00",
                "gstin": "29AABCC1234D1Z7",
                "pan": "AABCC1234D",
                "ifsc": "SBIN0001234",
                "bank_account": "987654321012",
                "gst_rate": "18",
            },
        },
        "bill_messy.pdf": {
            "expected_type": "Bill",
            "key_fields": {
                "bill_number": "BL/MYS/99",
                "amount": "245600.00",
                "ifsc": "KARB0000123",
                "bank_account": "1234567890123",
            },
        },
        "voucher_001.pdf": {
            "expected_type": "Voucher",
            "key_fields": {
                "voucher_number": "VR-2024-0042",
                "document_date": "2024-06-22",
                "amount": "125000.00",
                "cheque_number": "542109",
            },
        },
        "work_order_001.pdf": {
            "expected_type": "Work Order",
            "key_fields": {
                "work_order_number": "WO/ZP/MYS/2024/77",
                "document_date": "2024-04-02",
                "amount": "1450000.00",
            },
        },
        "sanction_order_001.pdf": {
            "expected_type": "Sanction Order",
            "key_fields": {
                "sanction_number": "AS/RDPR/15FC/2024/104",
                "document_date": "2024-04-10",
                "amount": "2500000.00",
            },
        },
        "tender_notice_001.pdf": {
            "expected_type": "Tender",
            "key_fields": {
                "tender_number": "NIT/MYS/2024/T-18",
                "document_date": "2024-01-15",
                "amount": "1820000.00",
            },
        },
        "measurement_book_001.pdf": {
            "expected_type": "Measurement Book",
            "key_fields": {
                "document_date": "2024-07-18",
                "amount": "315400.00",
            },
        },
        "completion_cert_001.pdf": {
            "expected_type": "Completion Certificate",
            "key_fields": {
                "amount": "890000.00",
            },
        },
        "utilization_cert_001.pdf": {
            "expected_type": "Utilization Certificate",
            "key_fields": {
                "document_date": "2024-03-31",
            },
        },
        "cash_book_2024.xlsx": {
            "expected_type": "Cash Book",
            "is_tabular": True,
        },
        "ledger_2024.xlsx": {
            "expected_type": "Ledger",
            "is_tabular": True,
        },
        "bank_statement_mysuru.csv": {
            "expected_type": "Bank Statement",
            "is_tabular": True,
        },
    }

    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"[OK] Generated {len(ground_truth) + 3} sample files in: {SAMPLE_FILES_DIR}")
    print(f"[OK] Generated ground truth specifications in: {GROUND_TRUTH_FILE}")


if __name__ == "__main__":
    generate_all_samples()
