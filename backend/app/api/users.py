from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleCode, get_current_user, require_roles
from app.models.user import Role, User
from app.schemas.common import RoleOut
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleCode.ADMINISTRATOR])),
):
    """Lists all registered users (Administrator only)."""
    users = (
        db.query(User)
        .filter(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .all()
    )
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleCode.ADMINISTRATOR])),
):
    """Creates a new user (Administrator only)."""
    user = UserService.create_user(
        db=db,
        user_in=user_in,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
    )
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleCode.ADMINISTRATOR])),
):
    """Updates user information and role assignment (Administrator only)."""
    user = UserService.update_user(
        db=db,
        user_id=user_id,
        user_in=user_in,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
    )
    return UserOut.model_validate(user)


@router.delete("/{user_id}", response_model=UserOut)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleCode.ADMINISTRATOR])),
):
    """Deactivates an active user (Administrator only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own active account",
        )
    user = UserService.deactivate_user(
        db=db,
        user_id=user_id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
    )
    return UserOut.model_validate(user)


@router.get("/roles", response_model=List[RoleOut])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns available roles in the system."""
    roles = db.query(Role).order_by(Role.name.asc()).all()
    return [RoleOut.model_validate(r) for r in roles]
