import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleCode, get_current_user, require_roles
from app.models.system import Holiday, Setting
from app.models.user import User
from app.schemas.settings import HolidayCreate, HolidayOut, SettingOut, SettingUpdate
from app.services.audit_trail import log_activity

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=List[SettingOut])
def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all system configuration parameters."""
    items = db.query(Setting).filter(Setting.deleted_at.is_(None)).order_by(Setting.category, Setting.key).all()
    return [SettingOut.model_validate(s) for s in items]


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    setting_in: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleCode.ADMINISTRATOR])),
):
    """Updates a system configuration setting (Administrator only)."""
    setting = (
        db.query(Setting)
        .filter(Setting.key == key, Setting.deleted_at.is_(None))
        .first()
    )
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting with key '{key}' not found",
        )

    if not setting.is_editable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Setting '{key}' is locked and cannot be edited",
        )

    # Validate JSON syntax
    try:
        json.loads(setting_in.value_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON string format: {str(e)}",
        )

    old_val = setting.value_json
    setting.value_json = setting_in.value_json
    setting.updated_by = current_user.id
    db.commit()
    db.refresh(setting)

    log_activity(
        db=db,
        action="setting:update",
        entity_type="setting",
        entity_id=setting.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={"key": key, "old_value": old_val, "new_value": setting.value_json},
    )
    return SettingOut.model_validate(setting)


@router.get("/holidays", response_model=List[HolidayOut])
def get_holidays(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the list of configured public holidays."""
    holidays = (
        db.query(Holiday)
        .filter(Holiday.deleted_at.is_(None))
        .order_by(Holiday.holiday_date.asc())
        .all()
    )
    return [HolidayOut.model_validate(h) for h in holidays]


@router.post("/holidays", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
def add_holiday(
    holiday_in: HolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleCode.ADMINISTRATOR])),
):
    """Adds a new public holiday to the governance calendar (Administrator only)."""
    existing = (
        db.query(Holiday)
        .filter(Holiday.holiday_date == holiday_in.holiday_date, Holiday.deleted_at.is_(None))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A holiday on this date already exists",
        )

    holiday = Holiday(
        holiday_date=holiday_in.holiday_date,
        name=holiday_in.name,
        state=holiday_in.state,
        description=holiday_in.description,
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)

    log_activity(
        db=db,
        action="holiday:create",
        entity_type="holiday",
        entity_id=holiday.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        payload={"date": str(holiday.holiday_date), "name": holiday.name},
    )
    return HolidayOut.model_validate(holiday)
