from enum import Enum
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

security = HTTPBearer()


class RoleCode(str, Enum):
    AUDITOR = "auditor"
    SENIOR_AUDITOR = "senior_auditor"
    AUDIT_OFFICER = "audit_officer"
    ADMINISTRATOR = "administrator"


# Documented Permission Matrix
# Role Permissions:
# - Administrator: Full user management, system settings, global case viewing
# - Audit Officer: Final approvals, sign-offs, finding settlement, report release
# - Senior Auditor: Case review, assignment, finding review, rule overrides
# - Auditor: Document upload, rule execution, finding draft/propose
PERMISSION_MATRIX = {
    RoleCode.ADMINISTRATOR: {
        "users:create", "users:read", "users:update", "users:delete",
        "settings:read", "settings:update",
        "audit_cases:read",
        "documents:read", "documents:upload",
        "audit_trail:verify", "audit_trail:read",
        "reports:read",
    },
    RoleCode.AUDIT_OFFICER: {
        "settings:read",
        "audit_cases:read", "audit_cases:approve",
        "documents:read", "documents:upload",
        "financial:read", "financial:verify",
        "findings:read", "findings:approve", "findings:settle",
        "reports:read", "reports:generate", "reports:approve", "reports:download",
        "audit_trail:verify", "audit_trail:read",
    },
    RoleCode.SENIOR_AUDITOR: {
        "settings:read",
        "audit_cases:read", "audit_cases:review", "audit_cases:assign",
        "documents:read", "documents:upload",
        "financial:read", "financial:verify",
        "findings:read", "findings:review", "findings:override",
        "reports:read", "reports:draft", "reports:generate", "reports:download",
        "audit_trail:verify", "audit_trail:read",
    },
    RoleCode.AUDITOR: {
        "settings:read",
        "audit_cases:read", "audit_cases:create", "audit_cases:edit",
        "documents:read", "documents:upload",
        "financial:read",
        "findings:read", "findings:propose",
        "reports:read", "reports:generate", "reports:download",
        "audit_trail:verify",
    },
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """Validates the Bearer access token and returns the active User object."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def require_roles(allowed_roles: List[str]) -> Callable:
    """Dependency factory checking that the current user possesses one of the allowed role codes."""
    allowed_set = {r.lower().replace(" ", "_") for r in allowed_roles} | {r.lower() for r in allowed_roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_code = current_user.role.code.lower() if current_user.role else ""
        if user_role_code not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{user_role_code}' lacks required permission",
            )
        return current_user

    return role_checker
