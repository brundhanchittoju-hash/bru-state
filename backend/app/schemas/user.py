from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from app.core.security import validate_password_policy
from app.schemas.common import DepartmentOut, ORMModel, RoleOut


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role_id: str
    department_id: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, v: str) -> str:
        validate_password_policy(v)
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[str] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, v: Optional[str]) -> Optional[str]:
        if v:
            validate_password_policy(v)
        return v


class UserOut(ORMModel):
    id: str
    email: EmailStr
    full_name: str
    role_id: str
    department_id: Optional[str] = None
    role: Optional[RoleOut] = None
    department: Optional[DepartmentOut] = None
    is_active: bool
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
