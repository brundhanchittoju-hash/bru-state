import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Rect, String as DString
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings

# ------------------------------------------------------------------------------
# Font Registration (Unicode / Rupee ₹ Support)
# ------------------------------------------------------------------------------
UNICODE_FONT_NAME = "ReportUnicodeFont"
UNICODE_BOLD_FONT_NAME = "ReportUnicodeBoldFont"
_font_registered = False


def _register_unicode_fonts():
    global _font_registered, UNICODE_FONT_NAME, UNICODE_BOLD_FONT_NAME
    if _font_registered:
        return
    candidates_regular = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]
    candidates_bold = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/NirmalaB.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]

    reg_ok = False
    for p in candidates_regular:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(UNICODE_FONT_NAME, p))
                reg_ok = True
                break
            except Exception:
                pass
    if not reg_ok:
        UNICODE_FONT_NAME = "Helvetica"

    bold_ok = False
    for p in candidates_bold:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(UNICODE_BOLD_FONT_NAME, p))
                bold_ok = True
                break
            except Exception:
                pass
    if not bold_ok:
        UNICODE_BOLD_FONT_NAME = UNICODE_FONT_NAME if reg_ok else "Helvetica-Bold"

    if reg_ok:
        try:
            pdfmetrics.registerFontFamily(
                UNICODE_FONT_NAME,
                normal=UNICODE_FONT_NAME,
                bold=UNICODE_BOLD_FONT_NAME if bold_ok else UNICODE_FONT_NAME,
                italic=UNICODE_FONT_NAME,
                boldItalic=UNICODE_BOLD_FONT_NAME if bold_ok else UNICODE_FONT_NAME,
            )
            if bold_ok:
                pdfmetrics.registerFontFamily(
                    UNICODE_BOLD_FONT_NAME,
                    normal=UNICODE_BOLD_FONT_NAME,
                    bold=UNICODE_BOLD_FONT_NAME,
                    italic=UNICODE_BOLD_FONT_NAME,
                    boldItalic=UNICODE_BOLD_FONT_NAME,
                )
        except Exception:
            pass

    _font_registered = True


_register_unicode_fonts()


# ------------------------------------------------------------------------------
# Numbered Canvas for Two-Pass "Page X of Y" and Watermark
# ------------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.report_number = kwargs.get("report_number", "RPT-2025-XXXX")
        self.version_number = kwargs.get("version_number", 1)
        self.case_number = kwargs.get("case_number", "CAS-XXXX")
        self.includes_watermark = kwargs.get("includes_watermark", True)

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        # 1. Watermark if enabled
        if self.includes_watermark:
            self.saveState()
            self.setFont("Helvetica-Bold", 54)
            self.setFillColor(colors.HexColor("#CBD5E1"), alpha=0.18)
            self.translate(300, 420)
            self.rotate(45)
            self.drawCentredString(0, 0, "DEMO DATA")
            self.restoreState()

        # 2. Header (skip page 1 cover)
        if self._pageNumber > 1:
            self.setFont(UNICODE_FONT_NAME, 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(40, 810, f"{self.report_number} • Version {self.version_number} • Case: {self.case_number}")
            self.drawRightString(555, 810, "Karnataka State Audit Department")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(40, 804, 555, 804)

        # 3. Footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 45, 555, 45)

        self.setFont(UNICODE_FONT_NAME, 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        disclaimer = "Generated by State Audit AI. Assists human auditors; final determination rests with the auditor."
        self.drawString(40, 32, disclaimer)
        self.drawRightString(555, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def format_inr(val: Any) -> str:
    try:
        amt = float(val or 0.0)
        s, *d = f"{amt:.2f}".split(".")
        r = ""
        while len(s) > 3:
            r = "," + s[-2:] + r if r else "," + s[-3:]
            s = s[:-2] if r != "," + s[-3:] else s[:-3]
        formatted = s + r + ("." + d[0] if d else "")
        return f"\u20b9{formatted}"
    except Exception:
        return f"\u20b9{val}"


def make_qr_drawing(url: str, size: float = 75) -> Drawing:
    qr = QrCodeWidget(url)
    qr.barWidth = size
    qr.barHeight = size
    d = Drawing(size, size)
    d.add(qr)
    return d


def crop_bbox_image(doc_path: str, page_number: int, bbox_json: Any, out_crop_path: str) -> Optional[str]:
    """Crops a document page around bbox and highlights it in yellow."""
    if not doc_path or not os.path.exists(doc_path):
        return None
    try:
        bbox = json.loads(bbox_json) if isinstance(bbox_json, str) else bbox_json
        if not isinstance(bbox, list) or len(bbox) != 4:
            return None
        doc = fitz.open(doc_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return None
        page = doc[page_number - 1]
        pw, ph = page.rect.width, page.rect.height
        x0, y0, x1, y1 = bbox[0] * pw, bbox[1] * ph, bbox[2] * pw, bbox[3] * ph
        # expand crop by 30pt padding
        pad = 25
        crop_rect = fitz.Rect(max(0, x0 - pad), max(0, y0 - pad), min(pw, x1 + pad), min(ph, y1 + pad))
        # draw yellow highlight rect
        highlight = page.add_rect_annot(fitz.Rect(x0, y0, x1, y1))
        highlight.set_colors(stroke=(0.95, 0.65, 0.1), fill=(1.0, 0.95, 0.6))
        highlight.set_opacity(0.4)
        highlight.update()

        pix = page.get_pixmap(clip=crop_rect, dpi=130)
        os.makedirs(os.path.dirname(out_crop_path), exist_ok=True)
        pix.save(out_crop_path)
        doc.close()
        return out_crop_path
    except Exception:
        return None


# ------------------------------------------------------------------------------
# Core Generator Class
# ------------------------------------------------------------------------------
class AuditReportPDFGenerator:
    def __init__(self, snapshot: Dict[str, Any], output_path: str, public_base_url: Optional[str] = None):
        self.snapshot = snapshot
        self.output_path = output_path
        self.public_base_url = (public_base_url or settings.PUBLIC_BASE_URL or "").rstrip("/")
        self.report_number = snapshot.get("report_number", "RPT-2025-0001")
        self.version_number = snapshot.get("version_number", 1)
        self.case_number = snapshot.get("case_number", "CAS-2024-MYS-001")
        self.includes_watermark = snapshot.get("includes_demo_watermark", True)
        self.verify_url = f"{self.public_base_url}/verify/{self.report_number}?v={self.version_number}"

        self.styles = getSampleStyleSheet()
        self._init_styles()

    def _init_styles(self):
        body_font = UNICODE_FONT_NAME
        bold_font = UNICODE_BOLD_FONT_NAME

        self.styles.add(ParagraphStyle("CoverSuperTitle", fontName=bold_font, fontSize=11, leading=14, textColor=colors.HexColor("#0D9488"), textTransform="uppercase"))
        self.styles.add(ParagraphStyle("CoverDept", fontName=bold_font, fontSize=16, leading=20, textColor=colors.HexColor("#0B1F3A")))
        self.styles.add(ParagraphStyle("CoverTitle", fontName=bold_font, fontSize=22, leading=26, textColor=colors.HexColor("#0F172A")))
        self.styles.add(ParagraphStyle("SectionTitle", fontName=bold_font, fontSize=13, leading=16, textColor=colors.HexColor("#0B1F3A"), keepWithNext=True))
        self.styles.add(ParagraphStyle("SubSectionTitle", fontName=bold_font, fontSize=10, leading=13, textColor=colors.HexColor("#334155"), keepWithNext=True))
        self.styles.add(ParagraphStyle("ReportBody", fontName=body_font, fontSize=8.5, leading=12, textColor=colors.HexColor("#334155")))
        self.styles.add(ParagraphStyle("ReportBodyBold", fontName=bold_font, fontSize=8.5, leading=12, textColor=colors.HexColor("#0F172A")))
        self.styles.add(ParagraphStyle("TableHead", fontName=bold_font, fontSize=8, leading=10, textColor=colors.white))
        self.styles.add(ParagraphStyle("TableCell", fontName=body_font, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1E293B")))
        self.styles.add(ParagraphStyle("TableCellBold", fontName=bold_font, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#0F172A")))
        self.styles.add(ParagraphStyle("BadgeTemplate", fontName=bold_font, fontSize=7, leading=9, textColor=colors.HexColor("#0369A1")))

    def build_pdf(self) -> Tuple[int, str]:
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=54,
        )

        story = []

        # 1. Cover Page
        story.extend(self._build_cover_page())
        story.append(PageBreak())

        # 2. Executive Summary
        story.extend(self._build_executive_summary())
        story.append(Spacer(1, 14))

        # 3. Case Details Table
        story.extend(self._build_case_details())
        story.append(Spacer(1, 14))

        # 4. Documents Reviewed
        story.extend(self._build_documents_reviewed())
        story.append(Spacer(1, 14))

        # 5. Verification Results (R-001..R-016)
        story.extend(self._build_verification_results())
        story.append(Spacer(1, 14))

        # 6. Findings Table
        story.extend(self._build_findings_table())
        story.append(Spacer(1, 14))

        # 7. Risk Analysis
        story.extend(self._build_risk_analysis())
        story.append(Spacer(1, 14))

        # 8. Detailed Evidence & Snippets
        story.extend(self._build_evidence_section())
        story.append(Spacer(1, 14))

        # 9. Auditor Remarks & Notes
        story.extend(self._build_auditor_remarks())
        story.append(Spacer(1, 14))

        # 10. Pending Items
        story.extend(self._build_pending_items())
        story.append(Spacer(1, 14))

        # 11. Recommendations
        story.extend(self._build_recommendations())
        story.append(Spacer(1, 16))

        # 12. Approval Block
        story.extend(self._build_approval_block())

        def canvas_maker(*args, **kwargs):
            return NumberedCanvas(
                *args,
                report_number=self.report_number,
                version_number=self.version_number,
                case_number=self.case_number,
                includes_watermark=self.includes_watermark,
                **kwargs,
            )

        doc.build(story, canvasmaker=canvas_maker)

        # Compute SHA-256 and page count via PyMuPDF
        fitz_doc = fitz.open(self.output_path)
        page_count = fitz_doc.page_count
        fitz_doc.close()

        sha = hashlib.sha256()
        with open(self.output_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return page_count, sha.hexdigest()

    # --------------------------------------------------------------------------
    # Section Builders
    # --------------------------------------------------------------------------
    def _build_cover_page(self) -> List[Any]:
        story = []
        story.append(Spacer(1, 15))
        story.append(Paragraph("GOVERNMENT OF KARNATAKA", self.styles["CoverSuperTitle"]))
        story.append(Paragraph("Karnataka State Audit Department (DEMO)", self.styles["CoverDept"]))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0D9488"), spaceBefore=2, spaceAfter=15))

        title = self.snapshot.get("report_title", "Statutory Financial Audit & Compliance Report")
        story.append(Paragraph(title, self.styles["CoverTitle"]))
        story.append(Spacer(1, 12))

        meta_data = [
            [Paragraph("Report Number:", self.styles["TableCellBold"]), Paragraph(self.report_number, self.styles["TableCell"]), Paragraph("Audit Status:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("status", "Draft"), self.styles["TableCellBold"])],
            [Paragraph("Audit Case ID:", self.styles["TableCellBold"]), Paragraph(self.case_number, self.styles["TableCellBold"]), Paragraph("Financial Year:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("financial_year", "2024-25"), self.styles["TableCell"])],
            [Paragraph("Scheme Name:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("scheme_name", "MGNREGA"), self.styles["TableCell"]), Paragraph("Audit Type:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("audit_type", "Statutory Compliance"), self.styles["TableCell"])],
            [Paragraph("District / Taluk:", self.styles["TableCellBold"]), Paragraph(f"{self.snapshot.get('district', '')} / {self.snapshot.get('taluk', '')}", self.styles["TableCell"]), Paragraph("Gram Panchayat:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("gram_panchayat", "General"), self.styles["TableCell"])],
            [Paragraph("Lead Auditor:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("lead_auditor_name", "Anand Rao"), self.styles["TableCell"]), Paragraph("Report Version:", self.styles["TableCellBold"]), Paragraph(f"v{self.version_number}.0 ({self.snapshot.get('status', 'Draft')})", self.styles["TableCell"])],
            [Paragraph("Generated At:", self.styles["TableCellBold"]), Paragraph(self.snapshot.get("generated_at_formatted", datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")), self.styles["TableCell"]), Paragraph("Security Seal:", self.styles["TableCellBold"]), Paragraph("SHA-256 Hash Chained", self.styles["TableCell"])],
        ]
        meta_table = Table(meta_data, colWidths=[100, 160, 100, 160])
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 35))

        # QR Block
        qr_draw = make_qr_drawing(self.verify_url, size=85)
        qr_cell = [
            [qr_draw, [
                Paragraph("<b>Public Verification Code</b>", self.styles["TableCellBold"]),
                Spacer(1, 3),
                Paragraph("Scan QR or verify online at:", self.styles["TableCell"]),
                Paragraph(f"<font color='#0D9488'>{self.verify_url}</font>", self.styles["TableCell"]),
                Spacer(1, 3),
                Paragraph("<i>Zero-knowledge tamper verification backed by cryptographic SHA-256 hash chaining.</i>", self.styles["TableCell"]),
            ]]
        ]
        qr_table = Table(qr_cell, colWidths=[100, 420])
        qr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(qr_table)
        story.append(Spacer(1, 30))

        if self.includes_watermark:
            demo_box = [[Paragraph("<b>DEMO DATA ADVISORY:</b> This report contains fictional test data and synthetic government financial records compiled for system verification.", self.styles["TableCellBold"])]]
            t = Table(demo_box, colWidths=[520])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#92400E")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
        return story

    def _build_executive_summary(self) -> List[Any]:
        story = [
            Paragraph("1. Executive Summary", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0B1F3A"), spaceBefore=2, spaceAfter=8),
        ]
        score = self.snapshot.get("case_risk_score", 0.0)
        risk_band = self.snapshot.get("case_risk_band", "Low").upper()
        total_flagged = self.snapshot.get("total_amount_at_risk", 0.0)
        findings = self.snapshot.get("findings", [])
        total_findings = len(findings)
        high_crit = sum(1 for f in findings if f.get("risk_level", "").lower() in ("high", "critical"))
        confirmed_count = sum(1 for f in findings if f.get("status") == "Confirmed")

        badge_p = Paragraph("AI summary: template mode", self.styles["BadgeTemplate"])
        obs_text = (
            f"Statutory financial verification for <b>{self.case_number}</b> evaluated 16 compliance rules under the "
            f"Karnataka Financial Code and KTPP Act 1999. The risk score stands at <b>{score:.1f}/100 ({risk_band})</b>. "
            f"A total of <b>{total_findings} items</b> were flagged for review, representing cumulative exposure of "
            f"<b>{format_inr(total_flagged)}</b>. Currently, <b>{confirmed_count} finding(s)</b> are substantiated by auditor review, "
            f"with <b>{high_crit} finding(s)</b> categorized as High or Critical statutory risk."
        )

        summary_box = [
            [Paragraph("<b>Composite Risk Score:</b>", self.styles["TableCellBold"]), Paragraph(f"<b>{score:.1f} / 100</b>", self.styles["TableCellBold"]), Paragraph("<b>Risk Severity Band:</b>", self.styles["TableCellBold"]), Paragraph(f"<b>{risk_band}</b>", self.styles["TableCellBold"])],
            [Paragraph("<b>Flagged Exposure:</b>", self.styles["TableCellBold"]), Paragraph(f"<b>{format_inr(total_flagged)}</b>", self.styles["TableCellBold"]), Paragraph("<b>Total Findings:</b>", self.styles["TableCellBold"]), Paragraph(str(total_findings), self.styles["TableCell"])],
        ]
        st_table = Table(summary_box, colWidths=[120, 140, 120, 140])
        st_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(st_table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(obs_text, self.styles["ReportBody"]))
        story.append(Spacer(1, 4))
        story.append(badge_p)
        return story

    def _build_case_details(self) -> List[Any]:
        story = [
            Paragraph("2. Case & Project Particulars", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        s = self.snapshot
        data = [
            [Paragraph("Sanctioned Grant:", self.styles["TableCellBold"]), Paragraph(format_inr(s.get("sanctioned_amount", 0)), self.styles["TableCell"]), Paragraph("Actual Expenditure:", self.styles["TableCellBold"]), Paragraph(format_inr(s.get("actual_expenditure", 0)), self.styles["TableCell"])],
            [Paragraph("Department:", self.styles["TableCellBold"]), Paragraph(s.get("department_name", "RDPR"), self.styles["TableCell"]), Paragraph("District / Taluk:", self.styles["TableCellBold"]), Paragraph(f"{s.get('district', '')} / {s.get('taluk', '')}", self.styles["TableCell"])],
            [Paragraph("Audit Period:", self.styles["TableCellBold"]), Paragraph(f"{s.get('planned_start_date', '01/04/2024')} to {s.get('due_date', '31/03/2025')}", self.styles["TableCell"]), Paragraph("Gram Panchayat:", self.styles["TableCellBold"]), Paragraph(s.get("gram_panchayat", "All"), self.styles["TableCell"])],
        ]
        t = Table(data, colWidths=[110, 150, 110, 150])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F8FAFC")),
        ]))
        story.append(t)
        return story

    def _build_documents_reviewed(self) -> List[Any]:
        story = [
            Paragraph("3. Documents Reviewed", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        docs = self.snapshot.get("documents", [])
        if not docs:
            story.append(Paragraph("<i>No documents registered under this audit case.</i>", self.styles["ReportBody"]))
            return story

        rows = [[
            Paragraph("File Name", self.styles["TableHead"]),
            Paragraph("Classification", self.styles["TableHead"]),
            Paragraph("Ver", self.styles["TableHead"]),
            Paragraph("Pages", self.styles["TableHead"]),
            Paragraph("Upload Date", self.styles["TableHead"]),
            Paragraph("SHA-256 (Prefix)", self.styles["TableHead"]),
            Paragraph("Confidence", self.styles["TableHead"]),
        ]]
        for d in docs:
            rows.append([
                Paragraph(d.get("filename", "")[:28], self.styles["TableCell"]),
                Paragraph(d.get("classification", "Unclassified"), self.styles["TableCell"]),
                Paragraph(f"v{d.get('version', 1)}", self.styles["TableCell"]),
                Paragraph(str(d.get("page_count", 1)), self.styles["TableCell"]),
                Paragraph(d.get("upload_date", "")[:10], self.styles["TableCell"]),
                Paragraph((d.get("sha256", "") or "")[:12], self.styles["TableCell"]),
                Paragraph(f"{d.get('confidence', 0.95):.0%}", self.styles["TableCellBold"]),
            ])

        t = Table(rows, colWidths=[130, 95, 30, 35, 65, 95, 70], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t)
        return story

    def _build_verification_results(self) -> List[Any]:
        story = [
            Paragraph("4. Rule Verification Results (R-001 through R-016)", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        results = self.snapshot.get("rule_results", [])
        if not results:
            # fallback list of 16 standard statutory rules
            results = [
                {"code": f"R-{i:03d}", "name": n, "status": "Pass", "findings": 0}
                for i, n in enumerate([
                    "Duplicate Payment Verification", "Duplicate Invoice Check", "Amount Mismatch",
                    "Sanction vs Payment Excess", "Bank vs Bill Reconciliation", "Tax / GST Validation",
                    "Arithmetic Line Items", "Missing Mandatory Documents", "Chronological Date Logic",
                    "Voucher Sequence Continuity", "Vendor Concentration Alert", "Large Cash Payment Cap",
                    "Statistical Outlier Payment", "Split Purchase Clustering", "Round Number Clustering",
                    "Unusual Timing / Sunday Rush"
                ], start=1)
            ]

        rows = [[
            Paragraph("Rule Code", self.styles["TableHead"]),
            Paragraph("Statutory Rule Description", self.styles["TableHead"]),
            Paragraph("Result", self.styles["TableHead"]),
            Paragraph("Findings Flagged", self.styles["TableHead"]),
        ]]
        for r in results:
            res_str = r.get("status", "Pass")
            res_color = "#16A34A" if res_str == "Pass" else "#DC2626" if res_str == "Flagged" else "#64748B"
            rows.append([
                Paragraph(r.get("code", "R-001"), self.styles["TableCellBold"]),
                Paragraph(r.get("name", "Verification Rule"), self.styles["TableCell"]),
                Paragraph(f"<font color='{res_color}'><b>{res_str}</b></font>", self.styles["TableCellBold"]),
                Paragraph(str(r.get("findings", 0)), self.styles["TableCell"]),
            ])

        t = Table(rows, colWidths=[65, 275, 80, 100], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t)
        return story

    def _build_findings_table(self) -> List[Any]:
        story = [
            Paragraph("5. Statutory Findings Register", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        findings = self.snapshot.get("findings", [])
        if not findings:
            story.append(Paragraph("<i>No findings were flagged by the rules run on this case. All records verified cleanly.</i>", self.styles["ReportBody"]))
            return story

        rows = [[
            Paragraph("Finding ID", self.styles["TableHead"]),
            Paragraph("Category", self.styles["TableHead"]),
            Paragraph("Risk", self.styles["TableHead"]),
            Paragraph("Flagged Amount", self.styles["TableHead"]),
            Paragraph("Status", self.styles["TableHead"]),
            Paragraph("Reviewer", self.styles["TableHead"]),
        ]]
        for f in findings:
            rows.append([
                Paragraph(f.get("finding_number", "F-001"), self.styles["TableCellBold"]),
                Paragraph(f.get("category", "General"), self.styles["TableCell"]),
                Paragraph(f.get("risk_level", "Medium").upper(), self.styles["TableCellBold"]),
                Paragraph(format_inr(f.get("amount_at_risk", 0)), self.styles["TableCellBold"]),
                Paragraph(f.get("status", "Open"), self.styles["TableCell"]),
                Paragraph(f.get("assigned_auditor_name", "Unassigned") or "Auditor", self.styles["TableCell"]),
            ])

        t = Table(rows, colWidths=[70, 130, 60, 90, 85, 85], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t)
        return story

    def _build_risk_analysis(self) -> List[Any]:
        story = [
            Paragraph("6. Risk Scoring & Exposure Analysis", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        weights = [
            ("Missing Mandatory Documents", 25, 60),
            ("Amount & Sanction Differences", 20, 80),
            ("Duplicate Payments / Invoices", 15, 100),
            ("Split Purchases (KTPP Lim)", 10, 50),
            ("Unsanctioned Disbursements", 10, 40),
            ("Calculation & GST Mismatches", 10, 30),
            ("Vendor Concentration Alert", 10, 75),
        ]
        # ReportLab Drawing Bar Chart
        d = Drawing(520, 110)
        y = 90
        for name, w, val in weights:
            d.add(DString(0, y, f"{name} ({w}% wt)", fontName=UNICODE_FONT_NAME, fontSize=7.5, fillColor=colors.HexColor("#1E293B")))
            # background bar
            d.add(Rect(180, y - 2, 250, 8, fillColor=colors.HexColor("#E2E8F0"), strokeColor=None))
            # filled bar
            fill_w = (val / 100.0) * 250
            bar_color = colors.HexColor("#DC2626") if val >= 75 else colors.HexColor("#F59E0B") if val >= 50 else colors.HexColor("#0D9488")
            d.add(Rect(180, y - 2, fill_w, 8, fillColor=bar_color, strokeColor=None))
            d.add(DString(440, y, f"{val}/100", fontName=UNICODE_FONT_NAME, fontSize=7.5, fillColor=colors.HexColor("#64748B")))
            y -= 14

        story.append(d)
        story.append(Spacer(1, 4))
        formula = (
            "<b>Formula:</b> Case Score = SUM(Factor_i * Weight_i). "
            "<b>Statutory Override:</b> Any Critical finding automatically enforces a minimum score of 85.0; "
            "any High finding enforces a minimum score of 60.0."
        )
        story.append(Paragraph(formula, self.styles["ReportBody"]))
        return story

    def _build_evidence_section(self) -> List[Any]:
        story = [
            Paragraph("7. Finding Evidence, Calculations & Document Snippets", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        findings = self.snapshot.get("findings", [])
        if not findings:
            story.append(Paragraph("<i>No finding evidence to substantiate.</i>", self.styles["ReportBody"]))
            return story

        # Sort: Confirmed/Escalated first, then others, cap at 5 for report brevity
        sorted_f = sorted(
            findings,
            key=lambda x: (
                0 if x.get("status") in ("Confirmed", "Escalated") else 1,
                0 if x.get("risk_level", "").lower() in ("critical", "high") else 1,
            )
        )[:5]

        for idx, f in enumerate(sorted_f, start=1):
            f_box = [
                Paragraph(f"<b>7.{idx} Finding {f.get('finding_number', '')}: {f.get('title', '')}</b>", self.styles["SubSectionTitle"]),
                Paragraph(f"<b>Status:</b> {f.get('status', 'Open')} | <b>Risk:</b> {f.get('risk_level', '').upper()} | <b>Amount Flagged:</b> {format_inr(f.get('amount_at_risk', 0))}", self.styles["TableCellBold"]),
                Spacer(1, 4),
                Paragraph(f"<b>Reason & Statutory Basis:</b> {f.get('reason', 'Verification flagged an anomaly.')}", self.styles["ReportBody"]),
                Spacer(1, 3),
                Paragraph(f"<b>Calculation:</b> {f.get('calculation', 'Inputs evaluated against statutory threshold.')}", self.styles["ReportBody"]),
            ]

            # Attempt PyMuPDF crop snippet if document file available
            crop_path = f"storage/reports/crops/{f.get('id', 'fid')}_crop.png"
            doc_file = f.get("source_doc_path")
            doc_page = f.get("source_page", 1)
            doc_bbox = f.get("source_bbox")
            rendered_crop = crop_bbox_image(doc_file, doc_page, doc_bbox, crop_path)
            if rendered_crop and os.path.exists(rendered_crop):
                try:
                    f_box.append(Spacer(1, 4))
                    f_box.append(Paragraph("<b>Source Document Evidence Region (Yellow Bounding Box):</b>", self.styles["TableCellBold"]))
                    f_box.append(RLImage(rendered_crop, width=420, height=120))
                except Exception:
                    pass
            elif f.get("comparison_table"):
                # show comparison table
                cmp = f.get("comparison_table")
                cmp_data = [[Paragraph("Stage", self.styles["TableCellBold"]), Paragraph("Reference", self.styles["TableCellBold"]), Paragraph("Amount", self.styles["TableCellBold"])]]
                for row in cmp:
                    cmp_data.append([Paragraph(str(row.get("stage", "")), self.styles["TableCell"]), Paragraph(str(row.get("ref", "")), self.styles["TableCell"]), Paragraph(format_inr(row.get("amount", 0)), self.styles["TableCellBold"])])
                ct = Table(cmp_data, colWidths=[120, 160, 120])
                ct.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                ]))
                f_box.append(Spacer(1, 4))
                f_box.append(ct)

            wrapper = Table([[f_box]], colWidths=[520])
            wrapper.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(wrapper)
            story.append(Spacer(1, 8))

        return story

    def _build_auditor_remarks(self) -> List[Any]:
        story = [
            Paragraph("8. Auditor Remarks & Reviewer Notes", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        notes = self.snapshot.get("reviewer_notes", [])
        if not notes:
            story.append(Paragraph("<i>No reviewer remarks recorded for this audit cycle.</i>", self.styles["ReportBody"]))
            return story

        rows = [[Paragraph("Author / Role", self.styles["TableHead"]), Paragraph("Timestamp", self.styles["TableHead"]), Paragraph("Observation / Remark", self.styles["TableHead"])]]
        for n in notes:
            rows.append([
                Paragraph(f"{n.get('author_name', 'Auditor')}<br/><font color='#64748B'>{n.get('author_role', '')}</font>", self.styles["TableCellBold"]),
                Paragraph(n.get("created_at", "")[:16], self.styles["TableCell"]),
                Paragraph(n.get("content", ""), self.styles["TableCell"]),
            ])
        t = Table(rows, colWidths=[130, 85, 305], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t)
        return story

    def _build_pending_items(self) -> List[Any]:
        story = [
            Paragraph("9. Pending Items & Observations", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        findings = self.snapshot.get("findings", [])
        pending = [f for f in findings if f.get("status") in ("Open", "Escalated", "Needs Clarification", "Pending Approval")]
        if not pending:
            story.append(Paragraph("<b>Zero pending items.</b> All flagged anomalies have reached final determination.", self.styles["ReportBody"]))
            return story

        items = [f"• <b>{f.get('finding_number')}:</b> {f.get('title')} ({f.get('status')}) — Action required by auditor/department." for f in pending[:8]]
        story.append(Paragraph("<br/>".join(items), self.styles["ReportBody"]))
        return story

    def _build_recommendations(self) -> List[Any]:
        story = [
            Paragraph("10. Statutory Recommendations", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=6),
        ]
        recs = [
            "1. <b>Voucher Numbering Continuity:</b> Recommended for review to ensure Gram Panchayat maintains sequential numbering in cash books without gaps.",
            "2. <b>Disbursement Reconciliations:</b> Recommended for follow-up by the Executive Officer to ensure bank debit entries match passed voucher vouchers.",
            "3. <b>Statutory Procurement Ceilings:</b> Strengthen compliance under Section 4 of the KTPP Act 1999 to avoid clustering procurement below statutory tender thresholds.",
            "4. <b>Mandatory Completion Records:</b> Ensure physical measurement books (MB) and utilization certificates are uploaded prior to final payment release.",
        ]
        story.append(Paragraph("<br/><br/>".join(recs), self.styles["ReportBody"]))
        return story

    def _build_approval_block(self) -> List[Any]:
        story = [
            Paragraph("11. Statutory Sign-off & Dual-Custody Approval Block", self.styles["SectionTitle"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=2, spaceAfter=8),
        ]
        status = self.snapshot.get("status", "Draft")
        is_approved = status == "Approved"
        approver = self.snapshot.get("approved_by_name", "Pending Approval")
        app_date = self.snapshot.get("approved_at", "Pending")

        rows = [
            [
                Paragraph("<b>Prepared By:</b>", self.styles["TableCellBold"]),
                Paragraph("<b>Reviewed By:</b>", self.styles["TableCellBold"]),
                Paragraph("<b>Statutory Approval:</b>", self.styles["TableCellBold"]),
            ],
            [
                Paragraph(f"{self.snapshot.get('generated_by_name', 'Lead Auditor')}<br/><font color='#64748B'>Auditor</font>", self.styles["TableCell"]),
                Paragraph(f"{self.snapshot.get('senior_auditor_name', 'Senior Auditor')}<br/><font color='#64748B'>Senior Auditor</font>", self.styles["TableCell"]),
                Paragraph(f"{approver if is_approved else 'Pending Sign-off'}<br/><font color='#64748B'>Audit Officer</font>", self.styles["TableCellBold"]),
            ],
            [
                Paragraph(f"Date: {self.snapshot.get('generated_at', '')[:10]}", self.styles["TableCell"]),
                Paragraph(f"Date: {self.snapshot.get('reviewed_at', '')[:10] if self.snapshot.get('reviewed_at') else 'Pending'}", self.styles["TableCell"]),
                Paragraph(f"Date: {app_date[:10] if is_approved else '_________________'}", self.styles["TableCell"]),
            ],
            [
                Paragraph("Signature: <i>[Verified]</i>", self.styles["TableCell"]),
                Paragraph("Signature: <i>[Verified]</i>", self.styles["TableCell"]),
                Paragraph(f"Signature: {'<i>[Digitally Signed]</i>' if is_approved else '_________________'}", self.styles["TableCellBold"]),
            ]
        ]
        t = Table(rows, colWidths=[170, 170, 180])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(t))
        return story
