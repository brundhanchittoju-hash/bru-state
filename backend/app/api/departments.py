from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.user import Department, User
from app.schemas.common import DepartmentOut

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists registered departments and local body units."""
    depts = (
        db.query(Department)
        .filter(Department.deleted_at.is_(None))
        .order_by(Department.type.asc(), Department.name.asc())
        .all()
    )
    return [DepartmentOut.model_validate(d) for d in depts]
