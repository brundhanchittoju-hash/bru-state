from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RoleOut(ORMModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None


class DepartmentOut(ORMModel):
    id: str
    code: str
    name: str
    type: str
    district: Optional[str] = None
    parent_id: Optional[str] = None
