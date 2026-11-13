from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.audit_case import AuditCase
from app.models.document import Document
from app.models.financial import FinancialRecord, Vendor
from app.models.finding import Finding
from app.models.report import Report
from app.models.user import Department, User

router = APIRouter(prefix="/search", tags=["Global Search"])


class SearchResultItem(BaseModel):
    id: str
    entity_type: str
    title: str
    subtitle: Optional[str] = None
    badge: Optional[str] = None
    link: str


class SearchResponseOut(BaseModel):
    query: str
    basic_search_mode: bool = True
    total_results: int
    results: Dict[str, List[SearchResultItem]]


@router.get("", response_model=SearchResponseOut)
def global_search(
    q: str = Query(..., min_length=2, description="Search term across all entities"),
    entity_type: Optional[str] = Query(None, description="Optional entity filter: cases, vendors, departments, vouchers, bills, findings, reports"),
    limit_per_entity: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified global multi-entity search across Cases, Vendors, Departments, Vouchers, Bills, Findings, and Reports.
    Uses SQLite/Postgres pattern search with explicit basic_search_mode indicator.
    """
    term = f"%{q.strip()}%"
    results: Dict[str, List[SearchResultItem]] = {
        "cases": [],
        "vendors": [],
        "departments": [],
        "vouchers": [],
        "bills": [],
        "findings": [],
        "reports": [],
    }

    # 1. Audit Cases
    if not entity_type or entity_type.lower() == "cases":
        cases = (
            db.query(AuditCase)
            .filter(
                AuditCase.deleted_at.is_(None),
                (AuditCase.case_number.ilike(term))
                | (AuditCase.title.ilike(term))
                | (AuditCase.project_name.ilike(term))
                | (AuditCase.district.ilike(term)),
            )
            .limit(limit_per_entity)
            .all()
        )
        for c in cases:
            results["cases"].append(
                SearchResultItem(
                    id=c.id,
                    entity_type="cases",
                    title=f"{c.case_number}: {c.title}",
                    subtitle=f"{c.district or 'Karnataka'} • {c.scheme_name or 'Statutory'}",
                    badge=c.status.title(),
                    link=f"/cases/{c.id}",
                )
            )

    # 2. Vendors
    if not entity_type or entity_type.lower() == "vendors":
        vendors = (
            db.query(Vendor)
            .filter(
                Vendor.deleted_at.is_(None),
                (Vendor.legal_name.ilike(term))
                | (Vendor.pan.ilike(term))
                | (Vendor.gstn.ilike(term)),
            )
            .limit(limit_per_entity)
            .all()
        )
        for v in vendors:
            results["vendors"].append(
                SearchResultItem(
                    id=v.id,
                    entity_type="vendors",
                    title=v.legal_name,
                    subtitle=f"PAN: {v.pan or 'N/A'} • GSTIN: {v.gstn or 'N/A'}",
                    badge="High" if v.is_flagged else "Low",
                    link=f"/vendors/{v.id}",
                )
            )

    # 3. Departments
    if not entity_type or entity_type.lower() == "departments":
        depts = (
            db.query(Department)
            .filter(
                Department.deleted_at.is_(None),
                (Department.name.ilike(term)) | (Department.code.ilike(term)),
            )
            .limit(limit_per_entity)
            .all()
        )
        for d in depts:
            results["departments"].append(
                SearchResultItem(
                    id=d.id,
                    entity_type="departments",
                    title=d.name,
                    subtitle=f"Code: {d.code}",
                    badge="Department",
                    link=f"/cases?department={d.id}",
                )
            )

    # 4. Vouchers (FinancialRecord where record_type == 'voucher')
    if not entity_type or entity_type.lower() == "vouchers":
        vouchers = (
            db.query(FinancialRecord)
            .filter(
                FinancialRecord.deleted_at.is_(None),
                FinancialRecord.record_type == "voucher",
                (FinancialRecord.document_number.ilike(term))
                | (FinancialRecord.payment_reference.ilike(term)),
            )
            .limit(limit_per_entity)
            .all()
        )
        for vo in vouchers:
            results["vouchers"].append(
                SearchResultItem(
                    id=vo.id,
                    entity_type="vouchers",
                    title=f"Voucher #{vo.document_number or vo.id[:8]}",
                    subtitle=f"Payment Ref: {vo.payment_reference or 'N/A'} • Amount: ₹{float(vo.total_amount or 0):,.2f}",
                    badge=vo.record_type.title(),
                    link=f"/cases/{vo.case_id}?tab=financial",
                )
            )

    # 5. Bills (FinancialRecord where record_type == 'bill')
    if not entity_type or entity_type.lower() == "bills":
        bills = (
            db.query(FinancialRecord)
            .filter(
                FinancialRecord.deleted_at.is_(None),
                FinancialRecord.record_type == "bill",
                (FinancialRecord.document_number.ilike(term))
                | (FinancialRecord.payment_reference.ilike(term)),
            )
            .limit(limit_per_entity)
            .all()
        )
        for b in bills:
            results["bills"].append(
                SearchResultItem(
                    id=b.id,
                    entity_type="bills",
                    title=f"Bill #{b.document_number or b.id[:8]}",
                    subtitle=f"Invoice/Ref: {b.payment_reference or 'N/A'} • Amount: ₹{float(b.total_amount or 0):,.2f}",
                    badge=b.record_type.title(),
                    link=f"/cases/{b.case_id}?tab=financial",
                )
            )

    # 6. Findings
    if not entity_type or entity_type.lower() == "findings":
        findings = (
            db.query(Finding)
            .filter(
                Finding.deleted_at.is_(None),
                (Finding.finding_number.ilike(term))
                | (Finding.title.ilike(term))
                | (Finding.reason.ilike(term)),
            )
            .limit(limit_per_entity)
            .all()
        )
        for f in findings:
            results["findings"].append(
                SearchResultItem(
                    id=f.id,
                    entity_type="findings",
                    title=f"{f.finding_number or f.id[:8]}: {f.title}",
                    subtitle=f"Risk: {(f.risk_level or 'low').title()} • Amount: ₹{float(f.amount_at_risk or 0):,.2f}",
                    badge=f.status.title(),
                    link=f"/findings/{f.id}",
                )
            )

    # 7. Reports
    if not entity_type or entity_type.lower() == "reports":
        reports = (
            db.query(Report)
            .filter(
                Report.deleted_at.is_(None),
                Report.report_title.ilike(term),
            )
            .limit(limit_per_entity)
            .all()
        )
        for r in reports:
            results["reports"].append(
                SearchResultItem(
                    id=r.id,
                    entity_type="reports",
                    title=r.report_title,
                    subtitle=f"Type: {r.report_type} • Status: {r.status}",
                    badge=r.status.title(),
                    link=f"/cases/{r.case_id}?tab=reports",
                )
            )

    total_count = sum(len(items) for items in results.values())

    return SearchResponseOut(
        query=q,
        basic_search_mode=True,
        total_results=total_count,
        results=results,
    )
