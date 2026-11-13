from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.system import Job
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobStatusOut(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/{job_id}", response_model=JobStatusOut)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves live status and progress of an asynchronous processing job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusOut.model_validate(job)
