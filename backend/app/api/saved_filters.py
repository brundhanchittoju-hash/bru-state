import json
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models.system import SavedFilter, UserPreference
from app.models.user import User

router = APIRouter(prefix="", tags=["Saved Filters & Preferences"])


class SavedFilterCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    entity_type: str = Field(..., description="findings, cases, documents, etc.")
    filter_json: str = Field(..., description="JSON serialized filter state")


class PreferenceUpdateIn(BaseModel):
    preference_key: str = Field(..., min_length=1, max_length=100)
    preference_value: str = Field(..., description="Serialized value or setting string")


@router.get("/filters/saved")
def list_saved_filters(
    entity_type: str = Query("findings"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    filters = (
        db.query(SavedFilter)
        .filter(
            SavedFilter.user_id == current_user.id,
            SavedFilter.entity_type == entity_type,
            SavedFilter.deleted_at.is_(None)
        )
        .order_by(SavedFilter.created_at.desc())
        .all()
    )
    return [
        {
            "id": f.id,
            "name": f.name,
            "entity_type": f.entity_type,
            "filter_json": f.filter_json,
            "created_at": f.created_at.isoformat(),
        }
        for f in filters
    ]


@router.post("/filters/saved")
def save_filter(
    payload: SavedFilterCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        json.loads(payload.filter_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in filter_json.")

    filter_obj = SavedFilter(
        user_id=current_user.id,
        entity_type=payload.entity_type,
        name=payload.name,
        filter_json=payload.filter_json,
    )
    db.add(filter_obj)
    db.commit()
    db.refresh(filter_obj)

    return {
        "id": filter_obj.id,
        "name": filter_obj.name,
        "entity_type": filter_obj.entity_type,
        "filter_json": filter_obj.filter_json,
        "created_at": filter_obj.created_at.isoformat(),
    }


@router.delete("/filters/saved/{filter_id}")
def delete_saved_filter(
    filter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    f = db.query(SavedFilter).filter(
        SavedFilter.id == filter_id,
        SavedFilter.user_id == current_user.id,
        SavedFilter.deleted_at.is_(None)
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Saved filter not found.")

    f.soft_delete()
    db.commit()
    return {"message": "Saved filter deleted successfully."}


@router.get("/users/me/preferences")
def get_user_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prefs = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == current_user.id, UserPreference.deleted_at.is_(None))
        .all()
    )
    return {p.preference_key: p.preference_value for p in prefs}


@router.put("/users/me/preferences")
def update_user_preference(
    payload: PreferenceUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pref = (
        db.query(UserPreference)
        .filter(
            UserPreference.user_id == current_user.id,
            UserPreference.preference_key == payload.preference_key,
            UserPreference.deleted_at.is_(None)
        )
        .first()
    )
    if not pref:
        pref = UserPreference(
            user_id=current_user.id,
            preference_key=payload.preference_key,
            preference_value=payload.preference_value
        )
        db.add(pref)
    else:
        pref.preference_value = payload.preference_value

    db.commit()
    return {"preference_key": payload.preference_key, "preference_value": payload.preference_value}

