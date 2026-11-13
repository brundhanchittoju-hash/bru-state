from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr
from app.schemas.common import DepartmentOut, ORMModel, RoleOut


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role_id: str
    department_id: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[str] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


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
