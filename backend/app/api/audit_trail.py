from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.audit_trail import ActivityLog
from app.models.user import User
from app.services.audit_trail import verify_hash_chain

router = APIRouter(prefix="/audit-trail", tags=["Audit Trail"])


@router.get("/verify")
def verify_audit_trail_integrity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Cryptographically verifies the append-only activity log chain from genesis.
    Returns whether the ledger is verified and reports broken sequence entries if tampered.
    """
    result = verify_hash_chain(db)
    return result


@router.get("/logs")
def get_recent_activity_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves recent audit log entries."""
    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.sequence_id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "sequence_id": log.sequence_id,
            "timestamp": log.timestamp.isoformat(),
            "actor_id": log.actor_id,
            "actor_name": log.actor_name,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "case_id": log.case_id,
            "prev_hash": log.prev_hash,
            "current_hash": log.current_hash,
        }
        for log in logs
    ]
