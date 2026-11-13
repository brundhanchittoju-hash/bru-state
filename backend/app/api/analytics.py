from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.audit_case import AuditCase
from app.models.document import Document
from app.models.financial import FinancialRecord, Vendor
from app.models.finding import Finding
from app.models.rules import VerificationRule
from app.models.user import Department, User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ==============================================================================
# Schemas
# ==============================================================================

class DepartmentBreakdownItem(BaseModel):
    department_id: Optional[str] = None
    department_name: str
    findings_count: int
    flagged_amount: float
    cases_count: int


class RiskDistributionItem(BaseModel):
    category: str  # scheme name or department
    critical: int
    high: int
    medium: int
    low: int
    total: int


class MonthlyTrendItem(BaseModel):
    month: str  # YYYY-MM
    findings_count: int
    flagged_amount: float


class DocumentTypeItem(BaseModel):
    document_type: str
    count: int
    processed_count: int


class CaseCompletionItem(BaseModel):
    district: str
    total_cases: int
    completed_cases: int
    completion_rate_pct: float


class TopRuleItem(BaseModel):
    rule_code: str
    rule_name: str
    category: str
    findings_count: int
    total_amount: float
    avg_risk_score: float


class MissingDocItem(BaseModel):
    scheme_name: str
    missing_count: int


class VendorAnalysisItem(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: str
    findings_count: int
    total_flagged_amount: float
    max_risk_score: float


class AnalyticsAggregationsOut(BaseModel):
    department_breakdown: List[DepartmentBreakdownItem]
    risk_distribution: List[RiskDistributionItem]
    monthly_findings_trend: List[MonthlyTrendItem]
    document_types_processed: List[DocumentTypeItem]
    case_completion_rate: List[CaseCompletionItem]
    top_rules_triggered: List[TopRuleItem]
    missing_documents_analysis: List[MissingDocItem]
    vendor_analysis: List[VendorAnalysisItem]


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/aggregations", response_model=AnalyticsAggregationsOut)
def get_analytics_aggregations(
    financial_year: Optional[str] = None,
    district: Optional[str] = None,
    department_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes aggregated analytics across 8 core visual dimensions.
    Supports SQL filtering by financial year, district, and department.
    """
    # 1. Base Case filter query
    case_base = db.query(AuditCase).filter(AuditCase.deleted_at.is_(None))
    if financial_year:
        case_base = case_base.filter(AuditCase.financial_year == financial_year)
    if district:
        case_base = case_base.filter(AuditCase.district == district)
    if department_id:
        case_base = case_base.filter(AuditCase.department_id == department_id)

    case_ids_subq = case_base.with_entities(AuditCase.id).subquery()

    # 1. Department Breakdown
    dept_rows = (
        db.query(
            Department.id,
            Department.name,
            func.count(Finding.id.distinct()).label("findings_count"),
            func.coalesce(func.sum(Finding.amount_at_risk), 0.0).label("flagged_amount"),
            func.count(AuditCase.id.distinct()).label("cases_count"),
        )
        .select_from(Department)
        .outerjoin(AuditCase, (AuditCase.department_id == Department.id) & (AuditCase.deleted_at.is_(None)))
        .outerjoin(Finding, (Finding.case_id == AuditCase.id) & (Finding.deleted_at.is_(None)))
        .group_by(Department.id, Department.name)
        .all()
    )
    dept_breakdown = [
        DepartmentBreakdownItem(
            department_id=r[0],
            department_name=r[1],
            findings_count=int(r[2]),
            flagged_amount=round(float(r[3]), 2),
            cases_count=int(r[4]),
        )
        for r in dept_rows
    ]

    # 2. Risk Distribution by Scheme
    schemes = ["MGNREGA", "PMAY-G", "15th Finance Commission Grants", "Jal Jeevan Mission", "Swachh Bharat Mission (Gramin)"]
    risk_dist = []
    case_id_filter = select(case_ids_subq.c.id)
    for s in schemes:
        f_scheme_q = (
            db.query(Finding)
            .join(AuditCase, Finding.case_id == AuditCase.id)
            .filter(
                Finding.deleted_at.is_(None),
                AuditCase.scheme_name == s,
                Finding.case_id.in_(case_id_filter),
            )
        )
        c_count = f_scheme_q.filter(func.lower(Finding.risk_level) == "critical").count()
        h_count = f_scheme_q.filter(func.lower(Finding.risk_level) == "high").count()
        m_count = f_scheme_q.filter(func.lower(Finding.risk_level) == "medium").count()
        l_count = f_scheme_q.filter(func.lower(Finding.risk_level) == "low").count()
        risk_dist.append(
            RiskDistributionItem(
                category=s,
                critical=c_count,
                high=h_count,
                medium=m_count,
                low=l_count,
                total=c_count + h_count + m_count + l_count,
            )
        )

    # 3. Monthly Findings Trend (past 12 months)
    dialect_name = db.get_bind().dialect.name if db.get_bind() is not None else "sqlite"
    if dialect_name == "postgresql":
        month_expr = func.to_char(func.timezone("UTC", Finding.created_at), "YYYY-MM")
    else:
        month_expr = func.strftime("%Y-%m", Finding.created_at)

    now = datetime.now(timezone.utc)
    monthly_trend = []
    for i in range(11, -1, -1):
        target_month_date = now - timedelta(days=i * 30)
        month_str = target_month_date.strftime("%Y-%m")
        findings_in_month = (
            db.query(
                func.count(Finding.id),
                func.coalesce(func.sum(Finding.amount_at_risk), 0.0),
            )
            .filter(
                Finding.deleted_at.is_(None),
                Finding.case_id.in_(case_id_filter),
                month_expr == month_str,
            )
            .first()
        )
        cnt = int(findings_in_month[0] or 0)
        amt = float(findings_in_month[1] or 0.0)
        monthly_trend.append(
            MonthlyTrendItem(
                month=month_str,
                findings_count=cnt,
                flagged_amount=round(amt, 2),
            )
        )

    # 4. Document Types Processed
    doc_type_rows = (
        db.query(
            Document.document_type,
            func.count(Document.id).label("total_cnt"),
            func.sum(case((func.lower(Document.status) == "processed", 1), else_=0)).label("proc_cnt"),
        )
        .filter(Document.deleted_at.is_(None), Document.case_id.in_(case_id_filter))
        .group_by(Document.document_type)
        .all()
    )
    doc_types = [
        DocumentTypeItem(
            document_type=r[0] or "Unknown",
            count=int(r[1]),
            processed_count=int(r[2] or 0),
        )
        for r in doc_type_rows
    ]

    # 5. Case Completion Rate by District
    districts = ["Mysuru", "Belagavi", "Dharwad", "Tumakuru", "Kalaburagi"]
    completion_rates = []
    for dist in districts:
        c_dist_q = db.query(AuditCase).filter(AuditCase.deleted_at.is_(None), AuditCase.district == dist)
        if financial_year:
            c_dist_q = c_dist_q.filter(AuditCase.financial_year == financial_year)
        if department_id:
            c_dist_q = c_dist_q.filter(AuditCase.department_id == department_id)

        tot = c_dist_q.count()
        comp = c_dist_q.filter(func.lower(AuditCase.status).in_(["approved", "closed"])).count()
        rate = round((comp / tot * 100), 1) if tot > 0 else 0.0
        completion_rates.append(
            CaseCompletionItem(
                district=dist,
                total_cases=tot,
                completed_cases=comp,
                completion_rate_pct=rate,
            )
        )

    # 6. Top Rules Triggered
    rule_rows = (
        db.query(
            VerificationRule.rule_code,
            VerificationRule.name,
            func.coalesce(VerificationRule.scheme, "General").label("category"),
            func.count(Finding.id).label("cnt"),
            func.coalesce(func.sum(Finding.amount_at_risk), 0.0).label("amt"),
            func.coalesce(func.avg(Finding.confidence), 0.0).label("avg_score"),
        )
        .join(Finding, Finding.rule_id == VerificationRule.id)
        .filter(Finding.deleted_at.is_(None), Finding.case_id.in_(case_id_filter))
        .group_by(VerificationRule.rule_code, VerificationRule.name, VerificationRule.scheme)
        .order_by(func.count(Finding.id).desc())
        .limit(10)
        .all()
    )
    top_rules = [
        TopRuleItem(
            rule_code=r[0],
            rule_name=r[1],
            category=r[2],
            findings_count=int(r[3]),
            total_amount=round(float(r[4]), 2),
            avg_risk_score=round(float(r[5]), 1),
        )
        for r in rule_rows
    ]

    # 7. Missing Documents Analysis
    # Count of R-008 findings grouped by case scheme
    missing_rows = (
        db.query(
            AuditCase.scheme_name,
            func.count(Finding.id),
        )
        .join(Finding, Finding.case_id == AuditCase.id)
        .join(VerificationRule, Finding.rule_id == VerificationRule.id)
        .filter(
            Finding.deleted_at.is_(None),
            VerificationRule.rule_code == "R-008",
            AuditCase.id.in_(case_id_filter),
        )
        .group_by(AuditCase.scheme_name)
        .all()
    )
    missing_analysis = [
        MissingDocItem(
            scheme_name=r[0] or "Unassigned",
            missing_count=int(r[1]),
        )
        for r in missing_rows
    ]

    # 8. Vendor Analysis
    vendor_rows = (
        db.query(
            Vendor.id,
            Vendor.legal_name,
            func.count(FinancialRecord.id).label("f_count"),
            func.coalesce(func.sum(FinancialRecord.total_amount), 0.0).label("tot_amt"),
            case((Vendor.is_flagged == True, 85.0), else_=25.0).label("max_risk"),
        )
        .outerjoin(FinancialRecord, FinancialRecord.vendor_id == Vendor.id)
        .filter(Vendor.deleted_at.is_(None))
        .group_by(Vendor.id, Vendor.legal_name, Vendor.is_flagged)
        .order_by(func.coalesce(func.sum(FinancialRecord.total_amount), 0.0).desc())
        .limit(10)
        .all()
    )
    vendor_analysis = [
        VendorAnalysisItem(
            vendor_id=r[0],
            vendor_name=r[1],
            findings_count=int(r[2]),
            total_flagged_amount=round(float(r[3]), 2),
            max_risk_score=round(float(r[4]), 1),
        )
        for r in vendor_rows
    ]

    return AnalyticsAggregationsOut(
        department_breakdown=dept_breakdown,
        risk_distribution=risk_dist,
        monthly_findings_trend=monthly_trend,
        document_types_processed=doc_types,
        case_completion_rate=completion_rates,
        top_rules_triggered=top_rules,
        missing_documents_analysis=missing_analysis,
        vendor_analysis=vendor_analysis,
    )
