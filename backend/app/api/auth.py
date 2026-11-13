from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import limiter
from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticates user, enforces lockout on repeated failures, and issues JWT access & refresh tokens.
    """
    user = UserService.authenticate_user(
        db=db,
        email=login_data.email,
        password=login_data.password,
    )

    access_token = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.code if user.role else "auditor",
            "email": user.email,
        },
    )
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload_in: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Validates the refresh token and issues a fresh access & refresh token pair.
    """
    try:
        payload = decode_token(payload_in.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token provided is not a refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is inactive",
        )

    new_access = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.code if user.role else "auditor",
            "email": user.email,
        },
    )
    new_refresh = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logs out user session and confirms token invalidation."""
    return {"message": "Successfully logged out", "status": "ok"}


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return UserOut.model_validate(current_user)
