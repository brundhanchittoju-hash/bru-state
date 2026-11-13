from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase
from app.models.document import Document, DocumentAnnotation
from app.models.finding import Finding, FindingNote
from app.models.user import User
from app.services.audit_trail import log_activity

router = APIRouter(prefix="/findings", tags=["Finding Notes & Annotations"])

EDIT_WINDOW_HOURS = 24


class NoteCreateIn(BaseModel):
    content: str = Field(..., min_length=2)
    parent_id: Optional[str] = None


class NoteUpdateIn(BaseModel):
    content: str = Field(..., min_length=2)


class AnnotationAttachIn(BaseModel):
    annotation_id: Optional[str] = None
    document_id: Optional[str] = None
    page: Optional[int] = 1
    bbox: Optional[str] = None
    note: Optional[str] = None


def verify_case_unlocked(db: Session, case_id: str):
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if case and case.status in ("Approved", "Closed", "approved", "closed"):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Case {case.case_number} is locked. Modifications are disabled."
        )


@router.get("/{finding_id}/notes")
def list_finding_notes(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    notes = (
        db.query(FindingNote)
        .filter(FindingNote.finding_id == finding_id, FindingNote.deleted_at.is_(None))
        .order_by(FindingNote.created_at.asc())
        .all()
    )

    out = []
    for n in notes:
        out.append({
            "id": n.id,
            "finding_id": n.finding_id,
            "author_id": n.author_id,
            "author_name": n.author.full_name if n.author else "Auditor",
            "author_role": n.author.role.name if (n.author and n.author.role) else "Auditor",
            "parent_id": n.parent_id,
            "content": n.content,
            "edited_at": n.edited_at.isoformat() if n.edited_at else None,
            "created_at": n.created_at.isoformat(),
            "can_edit": (n.author_id == current_user.id or (current_user.role and current_user.role.code == "administrator"))
        })
    return out


@router.post("/{finding_id}/notes")
def add_finding_note(
    finding_id: str,
    payload: NoteCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    if payload.parent_id:
        parent = db.query(FindingNote).filter(FindingNote.id == payload.parent_id, FindingNote.deleted_at.is_(None)).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent note not found.")

    note = FindingNote(
        finding_id=finding.id,
        author_id=current_user.id,
        parent_id=payload.parent_id,
        content=payload.content,
    )
    db.add(note)
    db.flush()

    log_activity(
        db=db,
        action="ADD_FINDING_NOTE",
        entity_type="FindingNote",
        entity_id=note.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=finding.case_id,
        payload={
            "finding_id": finding.id,
            "finding_number": finding.finding_number,
            "parent_id": payload.parent_id,
            "content_length": len(payload.content),
        }
    )

    db.commit()
    db.refresh(note)

    return {
        "message": "Reviewer note added successfully.",
        "note": {
            "id": note.id,
            "finding_id": note.finding_id,
            "author_id": note.author_id,
            "author_name": current_user.full_name,
            "author_role": current_user.role.name if current_user.role else "Auditor",
            "parent_id": note.parent_id,
            "content": note.content,
            "created_at": note.created_at.isoformat(),
        }
    }


@router.patch("/{finding_id}/notes/{note_id}")
def edit_finding_note(
    finding_id: str,
    note_id: str,
    payload: NoteUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    note = db.query(FindingNote).filter(FindingNote.id == note_id, FindingNote.finding_id == finding_id, FindingNote.deleted_at.is_(None)).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    # Permissions & Edit window check
    is_admin = current_user.role and current_user.role.code == "administrator"
    if note.author_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own notes.")

    # 24-hour edit window
    if note.created_at:
        age = datetime.now(timezone.utc) - (note.created_at if note.created_at.tzinfo else note.created_at.replace(tzinfo=timezone.utc))
        if age > timedelta(hours=EDIT_WINDOW_HOURS) and not is_admin:
            raise HTTPException(status_code=400, detail=f"Notes cannot be edited after {EDIT_WINDOW_HOURS} hours.")

    note.content = payload.content
    note.edited_at = datetime.now(timezone.utc)

    log_activity(
        db=db,
        action="EDIT_FINDING_NOTE",
        entity_type="FindingNote",
        entity_id=note.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=finding.case_id,
        payload={"finding_number": finding.finding_number, "note_id": note.id}
    )

    db.commit()
    return {"message": "Note updated successfully.", "edited_at": note.edited_at.isoformat()}


@router.delete("/{finding_id}/notes/{note_id}")
def delete_finding_note(
    finding_id: str,
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    note = db.query(FindingNote).filter(FindingNote.id == note_id, FindingNote.finding_id == finding_id, FindingNote.deleted_at.is_(None)).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    is_admin = current_user.role and current_user.role.code == "administrator"
    if note.author_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own notes.")

    note.soft_delete()

    log_activity(
        db=db,
        action="DELETE_FINDING_NOTE",
        entity_type="FindingNote",
        entity_id=note.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        case_id=finding.case_id,
        payload={"finding_number": finding.finding_number, "note_id": note.id}
    )

    db.commit()
    return {"message": "Note soft-deleted successfully."}


@router.post("/{finding_id}/annotations")
def attach_finding_annotation(
    finding_id: str,
    payload: AnnotationAttachIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Administrator", "Audit Officer", "Senior Auditor", "Auditor"]))
):
    """
    Attaches an existing document annotation to a finding, or creates a new spatial annotation linked to this finding.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    verify_case_unlocked(db, finding.case_id)

    if payload.annotation_id:
        ann = db.query(DocumentAnnotation).filter(DocumentAnnotation.id == payload.annotation_id).first()
        if not ann:
            raise HTTPException(status_code=404, detail="Target annotation not found.")
        ann.finding_id = finding.id
    elif payload.document_id and payload.note:
        doc = db.query(Document).filter(Document.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Target document not found.")
        ann = DocumentAnnotation(
            document_id=doc.id,
            page=payload.page or 1,
            bbox=payload.bbox,
            note=payload.note,
            finding_id=finding.id,
            created_by=current_user.id,
        )
        db.add(ann)
    else:
        raise HTTPException(status_code=400, detail="Either annotation_id or (document_id, note) required.")

    db.commit()
    return {"message": "Annotation attached to finding successfully."}


@router.get("/{finding_id}/annotations")
def list_finding_annotations(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    finding = db.query(Finding).filter(Finding.id == finding_id, Finding.deleted_at.is_(None)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    annotations = db.query(DocumentAnnotation).filter(DocumentAnnotation.finding_id == finding.id).all()
    out = []
    for a in annotations:
        out.append({
            "id": a.id,
            "document_id": a.document_id,
            "document_title": a.document.title if a.document else None,
            "page": a.page,
            "bbox": a.bbox,
            "note": a.note,
            "created_by": a.creator.full_name if a.creator else None,
            "created_at": a.created_at.isoformat(),
        })
    return out
