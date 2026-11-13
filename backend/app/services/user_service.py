from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, validate_password_policy, verify_password
from app.models.user import Department, Role, User
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_trail import log_activity


class UserService:
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        user = (
            db.query(User)
            .filter(User.email == email.lower().strip(), User.deleted_at.is_(None))
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        now = datetime.now(timezone.utc)

        # Check account lockout
        if user.locked_until:
            locked_dt = user.locked_until
            if locked_dt.tzinfo is None:
                locked_dt = locked_dt.replace(tzinfo=timezone.utc)
            if locked_dt > now:
                minutes_left = int((locked_dt - now).total_seconds() / 60) + 1
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is temporarily locked due to consecutive failed attempts. Try again in {minutes_left} minutes.",
                )

        # Check password
        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
                log_activity(
                    db=db,
                    action="user:lockout",
                    entity_type="user",
                    entity_id=user.id,
                    actor_id=user.id,
                    actor_name=user.full_name,
                    payload={
                        "email": user.email,
                        "failed_attempts": user.failed_login_attempts,
                        "lockout_until": user.locked_until.isoformat(),
                    },
                )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Successful login: reset failed attempts
        if user.failed_login_attempts > 0 or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            db.commit()

        log_activity(
            db=db,
            action="user:login",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            actor_name=user.full_name,
            payload={"email": user.email},
        )
        return user

    @staticmethod
    def create_user(
        db: Session,
        user_in: UserCreate,
        actor_id: Optional[str] = None,
        actor_name: str = "System",
    ) -> User:
        clean_email = user_in.email.lower().strip()
        existing = db.query(User).filter(User.email == clean_email, User.deleted_at.is_(None)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

        role = db.query(Role).filter(Role.id == user_in.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified role does not exist",
            )

        if user_in.department_id:
            dept = db.query(Department).filter(Department.id == user_in.department_id).first()
            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified department does not exist",
                )

        try:
            validate_password_policy(user_in.password)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        new_user = User(
            email=clean_email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name.strip(),
            role_id=user_in.role_id,
            department_id=user_in.department_id,
            is_active=user_in.is_active,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        log_activity(
            db=db,
            action="user:create",
            entity_type="user",
            entity_id=new_user.id,
            actor_id=actor_id,
            actor_name=actor_name,
            payload={"email": new_user.email, "role": role.code},
        )
        return new_user

    @staticmethod
    def update_user(
        db: Session,
        user_id: str,
        user_in: UserUpdate,
        actor_id: Optional[str] = None,
        actor_name: str = "System",
    ) -> User:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        changes = {}
        if user_in.full_name is not None:
            user.full_name = user_in.full_name.strip()
            changes["full_name"] = user.full_name

        if user_in.role_id is not None:
            role = db.query(Role).filter(Role.id == user_in.role_id).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified role does not exist",
                )
            user.role_id = user_in.role_id
            changes["role_id"] = user_in.role_id

        if user_in.department_id is not None:
            dept = db.query(Department).filter(Department.id == user_in.department_id).first()
            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified department does not exist",
                )
            user.department_id = user_in.department_id
            changes["department_id"] = user_in.department_id

        if user_in.is_active is not None:
            user.is_active = user_in.is_active
            changes["is_active"] = user.is_active

        if user_in.password:
            try:
                validate_password_policy(user_in.password)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            user.hashed_password = get_password_hash(user_in.password)
            changes["password_updated"] = True

        db.commit()
        db.refresh(user)

        log_activity(
            db=db,
            action="user:update",
            entity_type="user",
            entity_id=user.id,
            actor_id=actor_id,
            actor_name=actor_name,
            payload=changes,
        )
        return user

    @staticmethod
    def set_user_password(
        db: Session,
        user_id: str,
        new_password: str,
        actor_id: Optional[str] = None,
        actor_name: str = "System",
    ) -> User:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        try:
            validate_password_policy(new_password)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        user.hashed_password = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
        db.refresh(user)

        log_activity(
            db=db,
            action="user:set_password",
            entity_type="user",
            entity_id=user.id,
            actor_id=actor_id,
            actor_name=actor_name,
            payload={"email": user.email, "password_reset": True},
        )
        return user

    @staticmethod
    def deactivate_user(
        db: Session,
        user_id: str,
        actor_id: Optional[str] = None,
        actor_name: str = "System",
    ) -> User:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.is_active = False
        db.commit()
        db.refresh(user)

        log_activity(
            db=db,
            action="user:deactivate",
            entity_type="user",
            entity_id=user.id,
            actor_id=actor_id,
            actor_name=actor_name,
            payload={"email": user.email},
        )
        return user
