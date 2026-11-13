import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase
from app.models.document import Document
from app.models.finding import Finding, FindingNote, FindingReview
from app.models.report import Report, ReportVersion
from app.models.rules import VerificationRule
from app.models.user import Department, User
from app.services.audit_trail import log_activity
from app.services.reporting.pdf_generator import AuditReportPDFGenerator
from app.services.storage import storage_service

router = APIRouter(tags=["Statutory Reports"])


class ReportGenerateRequest(BaseModel):
    report_type: str = "preliminary"  # preliminary, interim, final
    title: Optional[str] = None
    includes_demo_watermark: bool = True
    confirmed_checklist: bool = False


class ReportApproveRequest(BaseModel):
    comment: str


def _build_snapshot_dict(db: Session, case: AuditCase, current_user: User, report_number: str, version_number: int, report_title: str, report_type: str, includes_watermark: bool) -> Dict[str, Any]:
    findings = (
        db.query(Finding)
        .filter(Finding.case_id == case.id, Finding.deleted_at.is_(None))
        .order_by(Finding.confidence.desc())
        .all()
    )
    docs = (
        db.query(Document)
        .filter(Document.case_id == case.id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.asc())
        .all()
    )
    rules = db.query(VerificationRule).filter(VerificationRule.is_enabled == True).order_by(VerificationRule.rule_code).all()

    # Pre-aggregate rule findings
    rule_counts: Dict[str, int] = {}
    for f in findings:
        r_id = f.rule.rule_code if f.rule else (f.rule_id or "R-OTHER")
        rule_counts[r_id] = rule_counts.get(r_id, 0) + 1

    findings_list = []
    risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    status_counts: Dict[str, int] = {}
    total_amount = 0.0

    for f in findings:
        r_band = (f.risk_level or "Low").capitalize()
        if r_band in risk_counts:
            risk_counts[r_band] += 1
        st = f.status or "Open"
        status_counts[st] = status_counts.get(st, 0) + 1
        amt = float(f.amount_at_risk if f.amount_at_risk is not None else (f.financial_implication or 0.0))
        total_amount += amt

        # Get evidence snippet if available
        bbox = None
        ev_doc_id = None
        ev_doc_path = None
        ev_page = 1
        if f.evidence:
            ev = f.evidence[0]
            ev_doc_id = ev.document_id
            ev_page = ev.page_number or 1
            if ev.document and ev.document.versions:
                ev_doc_path = ev.document.versions[0].file_path

        r_code = f.rule.rule_code if f.rule else (f.rule_id or "R-001")
        findings_list.append({
            "finding_number": f.finding_number or f"FND-{f.id[:8]}",
            "rule_id": r_code,
            "title": f.title,
            "category": f.category or "Expenditure Anomaly",
            "risk_score": int(f.confidence or 75),
            "risk_level": r_band,
            "amount": amt,
            "status": st,
            "department": case.department.name if case.department else "Panchayat Raj",
            "evidence_summary": f.description or f"Flagged anomaly under statutory rule {r_code}.",
            "recommended_action": f.reason or "Recommended for review and physical verification.",
            "bbox": bbox,
            "doc_path": ev_doc_path,
            "doc_page": ev_page,
            "comparison_table": [
                {"stage": "Sanction Order", "ref": f"AS-{case.case_number[-4:]}", "amount": amt},
                {"stage": "Disbursement Entry", "ref": f"VCH-{f.finding_number[-4:] if f.finding_number else '001'}", "amount": amt},
            ] if amt > 0 else []
        })

    docs_list = []
    for d in docs:
        docs_list.append({
            "name": d.original_filename or d.title,
            "document_type": d.document_type or "Official Record",
            "file_size": d.file_size or 0,
            "page_count": d.page_count or 1,
            "created_at": d.created_at.strftime("%Y-%m-%d") if d.created_at else "",
            "status": d.status or "processed",
        })

    rule_results = []
    for r in rules:
        count = rule_counts.get(r.rule_code, 0)
        rule_results.append({
            "rule_code": r.rule_code,
            "rule_name": r.name,
            "category": r.scheme or "Statutory Compliance",
            "status": "FLAGGED" if count > 0 else "PASSED",
            "count": count,
            "severity": r.severity,
        })

    notes = (
        db.query(FindingNote)
        .join(Finding, FindingNote.finding_id == Finding.id)
        .filter(Finding.case_id == case.id)
        .order_by(FindingNote.created_at.desc())
        .limit(10)
        .all()
    )
    notes_list = [
        {
            "author_name": n.author.full_name if n.author else "Auditor",
            "author_role": n.author.role.name if n.author and n.author.role else "Auditor",
            "content": n.content,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "",
        }
        for n in notes
    ]

    dept_name = case.department.name if case.department else "Rural Development & Panchayat Raj"
    return {
        "report_number": report_number,
        "version_number": version_number,
        "case_number": case.case_number,
        "report_title": report_title,
        "report_type": report_type,
        "financial_year": case.financial_year or "2024-25",
        "scheme_name": case.scheme_name or "MGNREGA",
        "audit_type": case.audit_type or "Statutory Compliance",
        "department": dept_name,
        "district": case.district or "Mysuru",
        "taluk": case.taluk or "Mysuru Taluk",
        "gram_panchayat": case.gram_panchayat or "Demo Panchayat",
        "lead_auditor_name": current_user.full_name,
        "lead_auditor_role": current_user.role.name if current_user.role else "Auditor",
        "generated_by_name": current_user.full_name,
        "generated_at_formatted": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        "status": "Draft",
        "includes_demo_watermark": includes_watermark,
        "total_expenditure": float(case.actual_expenditure or case.sanctioned_amount or 0),
        "total_questioned": total_amount,
        "findings": findings_list,
        "documents": docs_list,
        "rules": rule_results,
        "reviewer_notes": notes_list,
        "risk_breakdown": risk_counts,
        "status_breakdown": status_counts,
    }


@router.get("/cases/{case_id}/reports/checklist")
def get_case_report_checklist(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Audit case not found")

    findings = db.query(Finding).filter(Finding.case_id == case.id, Finding.deleted_at.is_(None)).all()
    high_critical_open = [
        f for f in findings
        if (f.risk_level or "").lower() in ("high", "critical") and f.status in ("Open", "Escalated")
    ]
    unreviewed = [f for f in findings if not f.reviews or f.reviews[-1].action != "approved"]

    return {
        "case_id": case.id,
        "case_number": case.case_number,
        "total_findings": len(findings),
        "high_critical_open_count": len(high_critical_open),
        "unreviewed_count": len(unreviewed),
        "can_generate_final": len(high_critical_open) == 0,
        "blockers": [
            f"Finding {f.finding_number}: {f.title} ({f.risk_level}) is still open/escalated."
            for f in high_critical_open[:5]
        ],
    }


@router.post("/cases/{case_id}/reports/generate")
def generate_case_report(
    case_id: str,
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["auditor", "senior_auditor", "audit_officer", "administrator"])),
):
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Audit case not found")

    # Enforce watermark permission
    if not payload.includes_demo_watermark:
        user_role = (current_user.role.code if current_user.role else "").lower()
        if user_role not in ("senior_auditor", "audit_officer", "administrator"):
            raise HTTPException(
                status_code=403,
                detail="Only Senior Auditors or Audit Officers can generate official reports without the DEMO watermark.",
            )

    # Blocker gate for Final report
    findings = db.query(Finding).filter(Finding.case_id == case.id, Finding.deleted_at.is_(None)).all()
    high_critical_open = [
        f for f in findings
        if (f.risk_level or "").lower() in ("high", "critical") and f.status in ("Open", "Escalated")
    ]
    if payload.report_type.lower() == "final" and len(high_critical_open) > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate Final report: {len(high_critical_open)} high/critical findings remain open or unreviewed.",
        )

    # Look for existing report for this case
    report = db.query(Report).filter(Report.case_id == case.id, Report.deleted_at.is_(None)).first()
    if not report:
        total_reports = db.query(func.count(Report.id)).scalar() or 0
        year_str = datetime.now().strftime("%Y")
        report_number = f"RPT-{year_str}-{total_reports + 1:04d}"
        report_title = payload.title or f"Statutory Financial Audit Report — {case.title}"
        report = Report(
            case_id=case.id,
            report_number=report_number,
            report_title=report_title,
            report_type=payload.report_type,
            current_version=1,
            status="Draft",
            generated_by=current_user.id,
        )
        db.add(report)
        db.flush()
        new_version_num = 1
    else:
        new_version_num = report.current_version + 1
        report_number = report.report_number or f"RPT-2025-{new_version_num:04d}"
        report_title = payload.title or report.report_title
        report.report_title = report_title
        report.report_type = payload.report_type
        report.current_version = new_version_num
        report.status = "Draft"
        report.generated_by = current_user.id

        # Mark older draft versions as Superseded
        for v in report.versions:
            if v.status in ("Draft", "Pending Approval"):
                v.status = "Superseded"

    # Assemble snapshot
    snapshot = _build_snapshot_dict(
        db=db,
        case=case,
        current_user=current_user,
        report_number=report_number,
        version_number=new_version_num,
        report_title=report_title,
        report_type=payload.report_type,
        includes_watermark=payload.includes_demo_watermark,
    )

    # Generate PDF and store via active backend
    if storage_service.is_supabase:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            temp_pdf_path = tmp_pdf.name
        try:
            generator = AuditReportPDFGenerator(
                snapshot=snapshot,
                output_path=temp_pdf_path,
                public_base_url=settings.PUBLIC_BASE_URL,
            )
            page_count, pdf_sha256 = generator.build_pdf()
            file_size = os.path.getsize(temp_pdf_path)
            with open(temp_pdf_path, "rb") as f:
                pdf_bytes = f.read()

            report_storage_path = f"reports/{uuid.uuid4()}.pdf"
            storage_service.upload_bytes(report_storage_path, pdf_bytes, content_type="application/pdf")
        finally:
            if os.path.exists(temp_pdf_path):
                try:
                    os.unlink(temp_pdf_path)
                except Exception:
                    pass
    else:
        storage_reports_dir = os.path.join(settings.STORAGE_DIR, "reports")
        os.makedirs(storage_reports_dir, exist_ok=True)
        pdf_filename = f"{report.id}_v{new_version_num}.pdf"
        report_storage_path = os.path.join(storage_reports_dir, pdf_filename)

        generator = AuditReportPDFGenerator(
            snapshot=snapshot,
            output_path=report_storage_path,
            public_base_url=settings.PUBLIC_BASE_URL,
        )
        page_count, pdf_sha256 = generator.build_pdf()
        file_size = os.path.getsize(report_storage_path)

    # Create report version
    rep_version = ReportVersion(
        report_id=report.id,
        version_number=new_version_num,
        status="Draft",
        file_path=report_storage_path,
        pdf_storage_path=report_storage_path,
        file_size_bytes=file_size,
        page_count=page_count,
        pdf_sha256=pdf_sha256,
        snapshot_json=json.dumps(snapshot),
        includes_demo_watermark=payload.includes_demo_watermark,
        qr_verification_code=f"{settings.PUBLIC_BASE_URL}/verify/{report_number}?v={new_version_num}",
        generated_by_id=current_user.id,
    )
    db.add(rep_version)

    log_activity(
        db=db,
        action="REPORT_GENERATED",
        entity_type="Report",
        entity_id=report.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={
            "report_number": report_number,
            "version": new_version_num,
            "page_count": page_count,
            "pdf_sha256": pdf_sha256,
            "case_number": case.case_number,
        },
    )
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "report_number": report.report_number,
        "report_title": report.report_title,
        "report_type": report.report_type,
        "current_version": report.current_version,
        "status": report.status,
        "file_size_bytes": file_size,
        "page_count": page_count,
        "pdf_sha256": pdf_sha256,
        "qr_verification_code": rep_version.qr_verification_code,
    }


@router.get("/reports")
def list_reports(
    financial_year: Optional[str] = None,
    district: Optional[str] = None,
    case_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Report).join(AuditCase, Report.case_id == AuditCase.id).filter(Report.deleted_at.is_(None))

    if financial_year:
        q = q.filter(AuditCase.financial_year == financial_year)
    if district:
        q = q.filter(AuditCase.district == district)
    if case_id:
        q = q.filter(Report.case_id == case_id)
    if status_filter:
        q = q.filter(Report.status == status_filter)
    if search:
        s_term = f"%{search}%"
        q = q.filter(
            or_(
                Report.report_number.ilike(s_term),
                Report.report_title.ilike(s_term),
                AuditCase.case_number.ilike(s_term),
                AuditCase.title.ilike(s_term),
            )
        )

    total = q.count()
    if sort_order.lower() == "asc":
        q = q.order_by(getattr(Report, sort_by, Report.created_at).asc())
    else:
        q = q.order_by(getattr(Report, sort_by, Report.created_at).desc())

    reports = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in reports:
        latest_ver = r.versions[0] if r.versions else None
        items.append({
            "id": r.id,
            "report_number": r.report_number,
            "report_title": r.report_title,
            "report_type": r.report_type,
            "current_version": r.current_version,
            "status": r.status,
            "case_id": r.case_id,
            "case_number": r.case.case_number if r.case else "",
            "case_title": r.case.title if r.case else "",
            "department": r.case.department.name if r.case and r.case.department else "",
            "district": r.case.district if r.case else "",
            "financial_year": r.case.financial_year if r.case else "",
            "generated_by_name": r.generator.full_name if r.generator else "Auditor",
            "approved_by_name": r.approver.full_name if r.approver else None,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "page_count": latest_ver.page_count if latest_ver else 0,
            "pdf_sha256": latest_ver.pdf_sha256 if latest_ver else "",
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    # Summary strip stats
    all_reports = db.query(Report.status).filter(Report.deleted_at.is_(None)).all()
    status_summary = {"Draft": 0, "Approved": 0, "Final": 0, "Superseded": 0}
    for (st,) in all_reports:
        if st in status_summary:
            status_summary[st] += 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "status_summary": status_summary,
    }


@router.get("/cases/{case_id}/reports")
def get_case_reports(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Audit case not found")

    reports = (
        db.query(Report)
        .filter(Report.case_id == case_id, Report.deleted_at.is_(None))
        .order_by(Report.created_at.desc())
        .all()
    )

    result = []
    for r in reports:
        versions_list = []
        for v in r.versions:
            versions_list.append({
                "id": v.id,
                "version_number": v.version_number,
                "status": v.status,
                "file_size_bytes": v.file_size_bytes,
                "page_count": v.page_count,
                "pdf_sha256": v.pdf_sha256,
                "includes_demo_watermark": v.includes_demo_watermark,
                "generated_by_name": v.generator.full_name if v.generator else "Auditor",
                "generated_at": v.generated_at.isoformat() if v.generated_at else None,
                "approved_by_name": v.approver.full_name if v.approver else None,
                "approved_at": v.approved_at.isoformat() if v.approved_at else None,
                "approval_comment": v.approval_comment,
            })
        result.append({
            "id": r.id,
            "report_number": r.report_number,
            "report_title": r.report_title,
            "report_type": r.report_type,
            "current_version": r.current_version,
            "status": r.status,
            "generated_by_name": r.generator.full_name if r.generator else "Auditor",
            "approved_by_name": r.approver.full_name if r.approver else None,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "approval_comment": r.approval_comment,
            "versions": versions_list,
        })
    return result


@router.get("/reports/{id}")
def get_report_detail(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = (
        db.query(Report)
        .filter(or_(Report.id == id, Report.report_number == id), Report.deleted_at.is_(None))
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    versions_list = []
    for v in r.versions:
        versions_list.append({
            "id": v.id,
            "version_number": v.version_number,
            "status": v.status,
            "file_size_bytes": v.file_size_bytes,
            "page_count": v.page_count,
            "pdf_sha256": v.pdf_sha256,
            "includes_demo_watermark": v.includes_demo_watermark,
            "qr_verification_code": v.qr_verification_code,
            "generated_by_name": v.generator.full_name if v.generator else "Auditor",
            "generated_at": v.generated_at.isoformat() if v.generated_at else None,
            "approved_by_name": v.approver.full_name if v.approver else None,
            "approved_at": v.approved_at.isoformat() if v.approved_at else None,
            "approval_comment": v.approval_comment,
        })

    return {
        "id": r.id,
        "report_number": r.report_number,
        "report_title": r.report_title,
        "report_type": r.report_type,
        "current_version": r.current_version,
        "status": r.status,
        "case_id": r.case_id,
        "case_number": r.case.case_number if r.case else "",
        "case_title": r.case.title if r.case else "",
        "department": r.case.department.name if r.case and r.case.department else "",
        "district": r.case.district if r.case else "",
        "financial_year": r.case.financial_year if r.case else "",
        "generated_by_name": r.generator.full_name if r.generator else "Auditor",
        "approved_by_name": r.approver.full_name if r.approver else None,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "approval_comment": r.approval_comment,
        "versions": versions_list,
    }


@router.get("/reports/{id}/preview")
def preview_report(
    id: str,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Report).filter(or_(Report.id == id, Report.report_number == id), Report.deleted_at.is_(None)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    target_ver = None
    if version:
        for v in r.versions:
            if v.version_number == version:
                target_ver = v
                break
    else:
        target_ver = r.versions[0] if r.versions else None

    if not target_ver or not target_ver.file_path:
        raise HTTPException(status_code=404, detail="Report PDF file record not found")

    return storage_service.stream_report(
        file_path_or_key=target_ver.file_path,
        filename=f"{r.report_number}_v{target_ver.version_number}.pdf",
        disposition="inline",
    )


@router.get("/reports/{id}/download")
def download_report(
    id: str,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Report).filter(or_(Report.id == id, Report.report_number == id), Report.deleted_at.is_(None)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    target_ver = None
    if version:
        for v in r.versions:
            if v.version_number == version:
                target_ver = v
                break
    else:
        target_ver = r.versions[0] if r.versions else None

    if not target_ver or not target_ver.file_path:
        raise HTTPException(status_code=404, detail="Report PDF file record not found")

    log_activity(
        db=db,
        action="REPORT_DOWNLOADED",
        entity_type="Report",
        entity_id=r.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={"report_number": r.report_number, "version": target_ver.version_number},
    )
    db.commit()

    return storage_service.stream_report(
        file_path_or_key=target_ver.file_path,
        filename=f"Report_{r.report_number}_v{target_ver.version_number}.pdf",
        disposition="attachment",
    )


@router.post("/reports/{id}/approve")
def approve_report(
    id: str,
    payload: ReportApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["senior_auditor", "audit_officer", "administrator"])),
):
    r = db.query(Report).filter(or_(Report.id == id, Report.report_number == id), Report.deleted_at.is_(None)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    latest_ver = r.versions[0] if r.versions else None
    if not latest_ver:
        raise HTTPException(status_code=400, detail="Cannot approve report with no generated versions.")

    # Maker-checker validation: Self-approval forbidden
    if r.generated_by == current_user.id or latest_ver.generated_by_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Maker-checker violation: An auditor cannot approve their own report.",
        )

    now = datetime.now(timezone.utc)
    r.status = "Approved"
    r.approved_by = current_user.id
    r.approved_at = now
    r.approval_comment = payload.comment

    latest_ver.status = "Approved"
    latest_ver.approved_by_id = current_user.id
    latest_ver.approved_at = now
    latest_ver.approval_comment = payload.comment

    # Re-stamp PDF with digital signature block
    if latest_ver.snapshot_json and latest_ver.file_path:
        try:
            snapshot = json.loads(latest_ver.snapshot_json)
            snapshot["status"] = "Approved"
            snapshot["approved_by_name"] = current_user.full_name
            snapshot["approved_at"] = now.strftime("%Y-%m-%d %H:%M UTC")
            snapshot["approval_comment"] = payload.comment

            gen = AuditReportPDFGenerator(
                snapshot=snapshot,
                output_path=latest_ver.file_path,
                public_base_url=settings.PUBLIC_BASE_URL,
            )
            page_count, sha = gen.build_pdf()
            latest_ver.snapshot_json = json.dumps(snapshot)
            latest_ver.page_count = page_count
            latest_ver.pdf_sha256 = sha
            latest_ver.file_size_bytes = os.path.getsize(latest_ver.file_path)
        except Exception:
            pass  # Keep existing PDF if re-stamp encounters minor font issue

    log_activity(
        db=db,
        action="REPORT_APPROVED",
        entity_type="Report",
        entity_id=r.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={
            "report_number": r.report_number,
            "version": latest_ver.version_number,
            "comment": payload.comment,
            "pdf_sha256": latest_ver.pdf_sha256,
        },
    )
    db.commit()
    db.refresh(r)

    return {
        "id": r.id,
        "report_number": r.report_number,
        "status": r.status,
        "approved_by_name": current_user.full_name,
        "approved_at": now.isoformat(),
        "approval_comment": payload.comment,
        "pdf_sha256": latest_ver.pdf_sha256,
    }
