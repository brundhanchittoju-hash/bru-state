import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.financial import FinancialRecord, Transaction, Vendor, VendorAlias
from app.models.finding import Finding, FindingEvidence
from app.models.user import User

router = APIRouter(prefix="/vendors", tags=["Vendors"])

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


# ==============================================================================
# Schemas
# ==============================================================================

class VendorListItemOut(BaseModel):
    id: str
    canonical_name: str
    pan: Optional[str] = None
    gstin: Optional[str] = None
    state: Optional[str] = "Karnataka"
    risk_level: str
    total_spend: float
    findings_count: int
    records_count: int


class VendorAliasOut(BaseModel):
    id: str
    raw_name: str
    confidence_score: float
    source: str


class VendorDossierOut(BaseModel):
    id: str
    canonical_name: str
    pan: Optional[str] = None
    is_pan_valid: bool = False
    gstin: Optional[str] = None
    is_gstin_valid: bool = False
    state: Optional[str] = "Karnataka"
    risk_level: str
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    aliases: List[VendorAliasOut]
    total_spend: float
    total_records: int
    total_findings: int
    findings: List[Dict[str, Any]]
    recent_transactions: List[Dict[str, Any]]


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("", response_model=List[VendorListItemOut])
def list_vendors(
    search: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists resolved vendors with spend metrics and findings count."""
    q = db.query(Vendor).filter(Vendor.deleted_at.is_(None))
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (Vendor.legal_name.ilike(s)) | (Vendor.pan.ilike(s)) | (Vendor.gstn.ilike(s))
        )
    if risk_level:
        is_flag = (risk_level.lower() == "high")
        q = q.filter(Vendor.is_flagged == is_flag)

    vendors = q.order_by(Vendor.legal_name.asc()).offset(offset).limit(limit).all()

    out = []
    for v in vendors:
        # Calculate spend & records from FinancialRecord or Transaction
        spend_val = (
            db.query(func.coalesce(func.sum(FinancialRecord.total_amount), 0.0))
            .filter(FinancialRecord.vendor_id == v.id, FinancialRecord.deleted_at.is_(None))
            .scalar()
        )
        rec_count = (
            db.query(FinancialRecord)
            .filter(FinancialRecord.vendor_id == v.id, FinancialRecord.deleted_at.is_(None))
            .count()
        )
        # Findings count via FindingEvidence -> Transaction
        f_count = (
            db.query(FindingEvidence.finding_id.distinct())
            .join(Transaction, FindingEvidence.transaction_id == Transaction.id)
            .filter(Transaction.vendor_id == v.id)
            .count()
        )

        out.append(
            VendorListItemOut(
                id=v.id,
                canonical_name=v.legal_name,
                pan=v.pan,
                gstin=v.gstn,
                state="Karnataka",
                risk_level="high" if v.is_flagged else "low",
                total_spend=round(float(spend_val or 0.0), 2),
                findings_count=f_count,
                records_count=rec_count,
            )
        )
    return out


@router.get("/{vendor_id}", response_model=VendorDossierOut)
def get_vendor_dossier(
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves detailed vendor dossier including PAN/GSTIN validity, aliases, spend, and linked findings."""
    v = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    is_pan_valid = bool(v.pan and PAN_REGEX.match(v.pan.upper().strip()))
    is_gstin_valid = bool(v.gstn and GSTIN_REGEX.match(v.gstn.upper().strip()))

    aliases = (
        db.query(VendorAlias)
        .filter(VendorAlias.vendor_id == v.id, VendorAlias.deleted_at.is_(None))
        .all()
    )

    alias_out = [
        VendorAliasOut(
            id=a.id,
            raw_name=a.alias_name,
            confidence_score=float(a.confidence_score or 1.0),
            source=a.status or "confirmed",
        )
        for a in aliases
    ]

    spend_val = (
        db.query(func.coalesce(func.sum(FinancialRecord.total_amount), 0.0))
        .filter(FinancialRecord.vendor_id == v.id, FinancialRecord.deleted_at.is_(None))
        .scalar()
    )
    total_records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.vendor_id == v.id, FinancialRecord.deleted_at.is_(None))
        .count()
    )

    # Findings linked via FindingEvidence -> Transaction
    finding_ids = (
        db.query(FindingEvidence.finding_id.distinct())
        .join(Transaction, FindingEvidence.transaction_id == Transaction.id)
        .filter(Transaction.vendor_id == v.id)
        .all()
    )
    f_ids = [fid[0] for fid in finding_ids]
    findings = (
        db.query(Finding)
        .filter(Finding.id.in_(f_ids), Finding.deleted_at.is_(None))
        .all()
        if f_ids else []
    )
    findings_list = [
        {
            "id": f.id,
            "finding_number": f.finding_number or f.id[:8],
            "title": f.title,
            "case_id": f.case_id,
            "case_number": f.case.case_number if f.case else None,
            "rule_code": f.rule.rule_code if f.rule else None,
            "severity": f.risk_level,
            "risk_score": float(f.confidence or 0.0),
            "amount": float(f.amount_at_risk or 0.0),
            "status": f.status,
            "created_at": f.created_at,
        }
        for f in findings
    ]

    # Recent transactions
    records = (
        db.query(Transaction)
        .filter(Transaction.vendor_id == v.id, Transaction.deleted_at.is_(None))
        .order_by(Transaction.transaction_date.desc().nullslast())
        .limit(20)
        .all()
    )
    tx_list = [
        {
            "id": r.id,
            "record_type": "transaction",
            "record_number": r.voucher_no,
            "record_date": str(r.transaction_date) if r.transaction_date else None,
            "amount": float(r.amount or 0.0),
            "description": r.description,
            "case_id": r.case_id,
        }
        for r in records
    ]

    return VendorDossierOut(
        id=v.id,
        canonical_name=v.legal_name,
        pan=v.pan,
        is_pan_valid=is_pan_valid,
        gstin=v.gstn,
        is_gstin_valid=is_gstin_valid,
        state="Karnataka",
        risk_level="high" if v.is_flagged else "low",
        bank_account_number=v.bank_account_no,
        ifsc_code=v.bank_ifsc,
        aliases=alias_out,
        total_spend=round(float(spend_val or 0.0), 2),
        total_records=total_records,
        total_findings=len(findings),
        findings=findings_list,
        recent_transactions=tx_list,
    )
