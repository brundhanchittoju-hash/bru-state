import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import limiter
from app.core.database import get_db
from app.models.report import Report, ReportVersion
from app.services.audit_trail import log_activity

router = APIRouter(prefix="/verify", tags=["Public Verification"])


@router.get("/{report_id}")
@limiter.limit("60/minute")
def verify_report_metadata(
    request: Request,
    report_id: str,
    v: Optional[int] = Query(None, alias="v"),
    db: Session = Depends(get_db),
):
    """
    Public Zero-Knowledge Verification Endpoint.
    Never exposes finding details, questioned amounts, vendor identities, or document text.
    Returns only cryptographic seal and statutory case metadata.
    """
    r = (
        db.query(Report)
        .filter(
            or_(Report.report_number == report_id, Report.id == report_id),
            Report.deleted_at.is_(None),
        )
        .first()
    )
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official audit report not found with this identifier.",
        )

    target_ver = None
    if v is not None:
        for version in r.versions:
            if version.version_number == v:
                target_ver = version
                break
        if not target_ver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {v} not found for report {report_id}.",
            )
    else:
        target_ver = r.versions[0] if r.versions else None

    if not target_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generated version available for this report.",
        )

    case = r.case
    return {
        "valid": True,
        "report_number": r.report_number,
        "version_number": target_ver.version_number,
        "status": target_ver.status,
        "report_title": r.report_title,
        "case_number": case.case_number if case else "",
        "case_title": case.title if case else "",
        "department": case.department.name if case and case.department else "Karnataka State Audit Department",
        "district": case.district if case else "",
        "financial_year": case.financial_year if case else "",
        "generated_at": target_ver.generated_at.isoformat() if target_ver.generated_at else None,
        "approved_at": target_ver.approved_at.isoformat() if target_ver.approved_at else None,
        "approver_name": target_ver.approver.full_name if target_ver.approver else None,
        "pdf_sha256": target_ver.pdf_sha256,
        "is_demo_data": target_ver.includes_demo_watermark,
        "page_count": target_ver.page_count or 1,
    }


@router.post("/{report_id}/file")
@limiter.limit("30/minute")
async def verify_report_file(
    request: Request,
    report_id: str,
    v: Optional[int] = Query(None, alias="v"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Public File Integrity Verification Endpoint.
    Calculates SHA-256 in memory without writing to disk.
    Matches uploaded document checksum against the tamper-evident record.
    """
    r = (
        db.query(Report)
        .filter(
            or_(Report.report_number == report_id, Report.id == report_id),
            Report.deleted_at.is_(None),
        )
        .first()
    )
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official audit report not found with this identifier.",
        )

    target_ver = None
    if v is not None:
        for version in r.versions:
            if version.version_number == v:
                target_ver = version
                break
    else:
        target_ver = r.versions[0] if r.versions else None

    if not target_ver or not target_ver.pdf_sha256:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recorded cryptographic hash found for this report version.",
        )

    # In-memory checksum computation
    content = await file.read()
    uploaded_sha = hashlib.sha256(content).hexdigest()
    expected_sha = target_ver.pdf_sha256

    is_match = (uploaded_sha.lower() == expected_sha.lower())

    client_ip = request.client.host if request.client else "unknown"
    log_activity(
        db=db,
        action="PUBLIC_REPORT_VERIFIED",
        entity_type="Report",
        entity_id=r.id,
        actor_id=None,
        actor_name=f"Public Verification ({client_ip})",
        payload={
            "report_number": r.report_number,
            "version": target_ver.version_number,
            "is_match": is_match,
            "uploaded_sha256": uploaded_sha,
        },
    )
    db.commit()

    if is_match:
        return {
            "match": True,
            "message": "Cryptographic SHA-256 match confirmed. Document is authentic and untampered.",
            "report_number": r.report_number,
            "version_number": target_ver.version_number,
            "pdf_sha256": uploaded_sha,
        }
    else:
        return {
            "match": False,
            "message": "Checksum mismatch. The uploaded file has been modified or tampered with.",
            "expected_sha256": expected_sha,
            "uploaded_sha256": uploaded_sha,
        }
