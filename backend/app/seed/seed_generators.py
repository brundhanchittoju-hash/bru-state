"""seed_generators.py - Helpers for generating statutory PDFs, scanned pages,

spreadsheets and reports for STATE AUDIT AI full seed.
"""
import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_case import AuditCase
from app.models.document import Document, ExtractedField
from app.models.report import Report, ReportVersion
from app.models.user import User
from app.services.reporting.pdf_generator import AuditReportPDFGenerator


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 binary hash."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_scanned_pdf_page(filepath: str, title: str, lines: List[str], angle: float = 0.8) -> int:
    """Renders a page, converts to PIL image with slight rotation and noise to simulate a scan."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img = Image.new("RGB", (820, 1160), color=(250, 249, 246))
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([40, 40, 780, 44], fill=(70, 70, 70))
    draw.text((50, 60), "GOVERNMENT OF KARNATAKA (OFFICIAL RECORD)", fill=(40, 40, 40))
    draw.text((50, 90), f"DOCUMENT: {title.upper()}", fill=(20, 20, 20))
    draw.text((50, 115), "PHYSICALLY SCANNED COPY - DISTRICT AUDIT CELL", fill=(100, 100, 100))
    draw.rectangle([40, 140, 780, 142], fill=(160, 160, 160))

    y = 170
    for line in lines:
        draw.text((50, y), line, fill=(30, 30, 30))
        y += 28
        if y > 1050:
            break

    # Stamp watermark
    draw.text((450, 920), "[VERIFIED BY AUDIT CELL]", fill=(180, 50, 50))
    draw.text((450, 945), f"DATE: {date.today().isoformat()}", fill=(180, 50, 50))

    # Apply slight tilt to simulate manual scanner feeder
    rotated = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    rotated.save(filepath, "PDF", resolution=150.0)
    return os.path.getsize(filepath)


def generate_clean_pdf(filepath: str, title: str, doc_type: str, lines: List[str], fields: Dict[str, str]) -> int:
    """Renders a digital statutory PDF with ReportLab."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, title)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 735, f"TYPE: {doc_type.upper()} | DEMO AUDIT EVIDENCE")
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.2, 0.4, 0.6)
    c.line(50, 725, 560, 725)

    y = 695
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "STATUTORY PARTICULARS:")
    y -= 18

    c.setFont("Helvetica", 9)
    for k, v in fields.items():
        label = k.replace("_", " ").title()
        c.drawString(60, y, f"• {label}: {v}")
        y -= 16

    y -= 10
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(50, y, 560, y)
    y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "TRANSACTION / RECORD CONTENT:")
    y -= 18

    c.setFont("Helvetica", 9)
    for line in lines:
        c.drawString(60, y, line)
        y -= 18
        if y < 60:
            c.showPage()
            y = 750

    c.save()
    return os.path.getsize(filepath)


def generate_tabular_spreadsheet(filepath: str, sheet_title: str, headers: List[str], rows: List[List[Any]]) -> int:
    """Generates a real XLSX spreadsheet for register/cash-book evidence."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title[:30]
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(filepath)
    return os.path.getsize(filepath)


def ingest_seed_document(
    db: Session,
    case_id: str,
    title: str,
    filename: str,
    doc_type: str,
    fields: Dict[str, str],
    lines: List[str],
    is_scanned: bool = False,
    is_tabular: bool = False,
    tabular_data: Optional[Tuple[List[str], List[List[Any]]]] = None,
    uploader_id: Optional[str] = None,
) -> Document:
    """Creates a real physical file on disk and inserts Document + ExtractedFields into DB."""
    doc_dir = os.path.join(settings.STORAGE_DIR, case_id)
    os.makedirs(doc_dir, exist_ok=True)
    file_path = os.path.join(doc_dir, filename)

    if is_tabular and tabular_data:
        f_size = generate_tabular_spreadsheet(file_path, title, tabular_data[0], tabular_data[1])
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        page_count = 1
    elif is_scanned:
        f_size = generate_scanned_pdf_page(file_path, title, lines)
        mime_type = "application/pdf"
        page_count = 1
    else:
        f_size = generate_clean_pdf(file_path, title, doc_type, lines, fields)
        mime_type = "application/pdf"
        page_count = 1

    sha = compute_sha256(file_path)

    # Check if doc already exists for idempotency
    if not uploader_id:
        u = db.query(User).filter(User.email == "senior.auditor@stateaudit.kar.gov.in").first()
        uploader_id = u.id if u else "system"

    doc = db.query(Document).filter(Document.case_id == case_id, Document.title == title).first()
    if not doc:
        doc = Document(
            case_id=case_id,
            title=title,
            original_filename=filename,
            stored_filename=filename,
            document_type=doc_type,
            file_size=f_size,
            mime_type=mime_type,
            sha256_hash=sha,
            status="processed",
            page_count=page_count,
            uploader_id=uploader_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    else:
        doc.file_size = f_size
        doc.sha256_hash = sha
        doc.stored_filename = filename
        db.commit()

    # Seed extracted fields with bboxes
    db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
    for k, v in fields.items():
        ef = ExtractedField(
            document_id=doc.id,
            field_name=k,
            extracted_value=str(v),
            original_text=str(v),
            confidence=0.95,
            source_page=1,
            bbox=json.dumps([0.1, 0.2, 0.8, 0.25]),
            validation_status="valid",
        )
        db.add(ef)
    db.commit()
    return doc


def generate_seed_report(
    db: Session,
    case: AuditCase,
    report_number: str,
    title: str,
    version_no: int,
    status: str,
    generator_user: User,
    approver_user: Optional[User] = None,
    watermark: bool = True,
) -> ReportVersion:
    """Generates a real statutory PDF report and creates Report + ReportVersion."""
    report = db.query(Report).filter(Report.report_number == report_number).first()
    if not report:
        report = Report(
            report_number=report_number,
            case_id=case.id,
            report_title=title,
            report_type="Statutory Audit Report",
            current_version=version_no,
            status=status,
            generated_by=generator_user.id,
            approved_by=approver_user.id if approver_user else None,
            approved_at=datetime.now(timezone.utc) if approver_user else None,
            approval_comment="Statutory audit findings reviewed and certified under KAD Act." if approver_user else None,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
    else:
        report.current_version = max(report.current_version, version_no)
        if status in ("Approved", "Final"):
            report.status = status
            report.approved_by = approver_user.id if approver_user else report.approved_by
            report.approved_at = datetime.now(timezone.utc) if approver_user else report.approved_at
        db.commit()

    # Private report output path
    report_dir = os.path.join(settings.STORAGE_DIR, case.id, "reports")
    os.makedirs(report_dir, exist_ok=True)
    pdf_filename = f"{report_number}_v{version_no}.pdf"
    pdf_path = os.path.join(report_dir, pdf_filename)

    # Build snapshot
    from app.api.reports import _build_snapshot_dict
    snapshot = _build_snapshot_dict(
        db=db,
        case=case,
        current_user=generator_user,
        report_number=report_number,
        version_number=version_no,
        report_title=title,
        report_type="Statutory Audit Report",
        includes_watermark=watermark,
    )
    if approver_user:
        snapshot["approval"] = {
            "approved_by": approver_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "comment": "Statutory audit findings reviewed and certified under KAD Act.",
            "designation": approver_user.role.name if approver_user.role else "Audit Officer",
        }

    public_base = getattr(settings, "PUBLIC_BASE_URL", "http://localhost:5173")
    engine = AuditReportPDFGenerator(snapshot, pdf_path, public_base_url=public_base)
    page_count, pdf_sha256 = engine.build_pdf()
    file_size = os.path.getsize(pdf_path)

    # Check or create version
    r_ver = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report.id, ReportVersion.version_number == version_no)
        .first()
    )
    if not r_ver:
        r_ver = ReportVersion(
            report_id=report.id,
            version_number=version_no,
            status=status,
            file_path=pdf_path,
            pdf_storage_path=pdf_path,
            file_size_bytes=file_size,
            page_count=page_count,
            pdf_sha256=pdf_sha256,
            snapshot_json=json.dumps(snapshot),
            includes_demo_watermark=watermark,
            qr_verification_code=f"{public_base}/verify/{report.id}?v={version_no}",
            generated_by_id=generator_user.id,
            approved_by_id=approver_user.id if approver_user else None,
            approved_at=datetime.now(timezone.utc) if approver_user else None,
            approval_comment="Statutory audit findings reviewed and certified under KAD Act." if approver_user else None,
        )
        db.add(r_ver)
        db.commit()
        db.refresh(r_ver)
    else:
        r_ver.status = status
        r_ver.file_path = pdf_path
        r_ver.file_size_bytes = file_size
        r_ver.page_count = page_count
        r_ver.pdf_sha256 = pdf_sha256
        r_ver.snapshot_json = json.dumps(snapshot)
        r_ver.approved_by_id = approver_user.id if approver_user else r_ver.approved_by_id
        r_ver.approved_at = datetime.now(timezone.utc) if approver_user else r_ver.approved_at
        db.commit()

    return r_ver
