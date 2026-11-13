from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel
from app.schemas.common import ORMModel


class SettingOut(ORMModel):
    id: str
    key: str
    value_json: str
    category: str
    is_editable: bool
    updated_at: datetime


class SettingUpdate(BaseModel):
    value_json: str


class HolidayOut(ORMModel):
    id: str
    holiday_date: date
    name: str
    state: str
    description: Optional[str] = None


class HolidayCreate(BaseModel):
    holiday_date: date
    name: str
    state: str = "Karnataka"
    description: Optional[str] = None
