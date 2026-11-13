import os
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.rbac import get_current_user, require_roles
from app.models.audit_case import AuditCase
from app.models.document import Document, DocumentVersion, ExtractedField, DocumentAnnotation
from app.models.financial import Transaction
from app.models.system import Job
from app.models.user import User
from app.schemas.document import (
    DocumentOut,
    DocumentDetailOut,
    DocumentVersionOut,
    ExtractedFieldOut,
    DocumentAnnotationOut,
    FieldOverrideIn,
    FieldCreateIn,
    ReclassifyIn,
    AnnotationCreateIn,
    TabularImportIn,
)
from app.services.storage import StorageService, storage_service
from app.services.audit_trail import log_activity
from app.services.document_processor import process_document_pipeline
from app.services.extraction import (
    get_effective_field_value,
    parse_tabular_content,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


def _run_bg_pipeline(doc_id: str, job_id: str):
    """Worker function for FastAPI BackgroundTasks using fresh DB session."""
    db = SessionLocal()
    try:
        process_document_pipeline(db=db, document_id=doc_id, job_id=job_id)
    finally:
        db.close()


def _format_doc_out(doc: Document, db: Session, job_id: Optional[str] = None) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        case_id=doc.case_id,
        case_number=doc.case.case_number if doc.case else None,
        title=doc.title,
        original_filename=doc.original_filename,
        stored_filename=doc.stored_filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        sha256_hash=doc.sha256_hash,
        document_type=doc.document_type,
        status=doc.status,
        page_count=doc.page_count,
        current_version=doc.current_version,
        classification_confidence=doc.classification_confidence,
        classification_keywords=doc.classification_keywords,
        extractor_used=doc.extractor_used,
        processing_error=doc.processing_error,
        document_date=doc.document_date,
        uploader_id=doc.uploader_id,
        uploader_name=doc.uploader.full_name if doc.uploader else None,
        created_at=doc.created_at,
        job_id=job_id,
    )


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    case_id: str = Form(...),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    as_new_version_of: Optional[str] = Form(None),
    sync_process: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Securely uploads a document into private storage and enqueues extraction pipeline.
    Validates MIME type, extension, size limit, and prevents duplicate SHA-256 within the case.
    """
    case = db.query(AuditCase).filter(AuditCase.id == case_id, AuditCase.deleted_at.is_(None)).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified audit case not found",
        )

    if case.status and case.status.lower() in ["approved", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit case is locked ({case.status.title()}). Document uploads are prohibited on locked cases.",
        )

    content = await file.read()
    doc, _ = StorageService.save_file(
        db=db,
        case_id=case_id,
        upload_file=file,
        content=content,
        user_id=current_user.id,
        user_name=current_user.full_name,
        title=title,
        document_type=document_type,
        as_new_version_of=as_new_version_of,
    )

    # Automatically transition case status from 'draft' to 'documents_uploaded'
    if case.status == "draft":
        case.status = "documents_uploaded"
        db.commit()

    # Create background tracking job
    job = Job(
        job_type="document_extraction",
        payload_json=json.dumps({"document_id": doc.id, "case_id": case_id}),
        status="pending",
        progress=0,
        created_by=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Process either synchronously (for test/immediacy) or via background worker
    if sync_process:
        process_document_pipeline(db=db, document_id=doc.id, job_id=job.id)
        db.refresh(doc)
    else:
        background_tasks.add_task(_run_bg_pipeline, doc.id, job.id)

    return _format_doc_out(doc, db, job_id=job.id)


@router.get("", response_model=List[DocumentOut])
def list_documents(
    case_id: Optional[str] = None,
    document_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists documents with optional filtering and search."""
    query = db.query(Document).filter(Document.deleted_at.is_(None))

    if case_id:
        query = query.filter(Document.case_id == case_id)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (Document.title.ilike(search_fmt)) |
            (Document.original_filename.ilike(search_fmt))
        )

    docs = query.order_by(Document.created_at.desc()).all()
    return [_format_doc_out(d, db) for d in docs]


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full document details including versions, extracted fields, and annotations."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_number.desc())
        .all()
    )

    fields = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == doc.id, ExtractedField.deleted_at.is_(None))
        .order_by(ExtractedField.source_page.asc(), ExtractedField.field_name.asc())
        .all()
    )

    annotations = (
        db.query(DocumentAnnotation)
        .filter(DocumentAnnotation.document_id == doc.id, DocumentAnnotation.deleted_at.is_(None))
        .order_by(DocumentAnnotation.created_at.desc())
        .all()
    )

    base = _format_doc_out(doc, db)
    return DocumentDetailOut(
        **base.model_dump(),
        versions=[
            DocumentVersionOut(
                id=v.id,
                document_id=v.document_id,
                version_number=v.version_number,
                stored_filename=v.stored_filename,
                sha256_hash=v.sha256_hash,
                file_size=v.file_size,
                document_type=v.document_type,
                classification_confidence=v.classification_confidence,
                change_summary=v.change_summary,
                created_by=v.created_by,
                created_at=v.created_at,
            )
            for v in versions
        ],
        extracted_fields=[
            ExtractedFieldOut(
                id=f.id,
                document_id=f.document_id,
                field_name=f.field_name,
                original_text=f.original_text,
                extracted_value=f.extracted_value,
                corrected_value=f.corrected_value,
                effective_value=get_effective_field_value(f),
                is_overridden=f.is_overridden,
                overridden_by=f.overrider.full_name if f.overrider else None,
                override_comment=f.override_comment,
                confidence=f.confidence,
                source_page=f.source_page,
                bbox=f.bbox,
                extractor=f.extractor,
                validation_status=f.validation_status,
                validation_message=f.validation_message,
                extracted_at=f.extracted_at,
            )
            for f in fields
        ],
        annotations=[
            DocumentAnnotationOut(
                id=a.id,
                document_id=a.document_id,
                page=a.page,
                bbox=a.bbox,
                note=a.note,
                finding_id=a.finding_id,
                created_by=a.created_by,
                created_by_name=a.creator.full_name if a.creator else None,
                created_at=a.created_at,
            )
            for a in annotations
        ],
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Securely downloads an authenticated document (original or specific version)."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    stored_name = doc.stored_filename
    if version:
        v_rec = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == doc.id, DocumentVersion.version_number == version)
            .first()
        )
        if v_rec:
            stored_name = v_rec.stored_filename

    return storage_service.stream_file(
        stored_name=stored_name,
        case_id=doc.case_id,
        media_type=doc.mime_type,
        filename=doc.original_filename,
        disposition="attachment",
    )


@router.get("/{document_id}/pages/{page_num}/thumbnail")
def get_page_thumbnail(
    document_id: str,
    page_num: int,
    db: Session = Depends(get_db),
):
    """Serves the rendered page thumbnail image."""
    return storage_service.stream_thumbnail(
        document_id=document_id,
        page_num=page_num,
    )


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    sync_process: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor"])),
):
    """Triggers re-extraction on an existing document."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    job = Job(
        job_type="document_reprocess",
        payload_json=json.dumps({"document_id": doc.id, "case_id": doc.case_id}),
        status="pending",
        progress=0,
        created_by=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if sync_process:
        process_document_pipeline(db=db, document_id=doc.id, job_id=job.id)
    else:
        background_tasks.add_task(_run_bg_pipeline, doc.id, job.id)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="DOCUMENT_REPROCESSED",
        entity_type="document",
        entity_id=doc.id,
        case_id=doc.case_id,
        payload={"job_id": job.id},
    )

    return {"message": "Reprocessing initiated", "job_id": job.id}


@router.post("/{document_id}/reclassify")
def reclassify_document(
    document_id: str,
    payload: ReclassifyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Allows an auditor to manually override document classification with comment."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    old_type = doc.document_type
    doc.document_type = payload.document_type
    doc.classification_confidence = 1.0
    doc.extractor_used = "manual"
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="DOCUMENT_RECLASSIFIED",
        entity_type="document",
        entity_id=doc.id,
        case_id=doc.case_id,
        payload={
            "from_type": old_type,
            "to_type": payload.document_type,
            "comment": payload.comment,
        },
    )

    return {"message": "Document reclassified successfully", "document_type": doc.document_type}


@router.patch("/fields/{field_id}/override")
@router.post("/fields/{field_id}/override")
def override_field_direct(
    field_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    field = db.query(ExtractedField).filter(
        ExtractedField.id == field_id,
        ExtractedField.deleted_at.is_(None),
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    if field.document and field.document.case and field.document.case.status and field.document.case.status.lower() in ["approved", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit case is locked ({field.document.case.status.title()}). Field overrides are prohibited on locked cases.",
        )

    corrected_val = payload.get("corrected_value") or payload.get("override_value")
    comment_val = payload.get("comment") or payload.get("override_reason") or "Auditor override"

    old_effective = get_effective_field_value(field)
    field.corrected_value = corrected_val
    field.is_overridden = True
    field.overridden_by = current_user.id
    field.override_comment = comment_val
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="FIELD_OVERRIDDEN",
        entity_type="extracted_field",
        entity_id=field.id,
        case_id=field.document.case_id if field.document else None,
        payload={
            "field_name": field.field_name,
            "previous_value": old_effective,
            "corrected_value": corrected_val,
            "comment": comment_val,
        },
    )

    return {
        "message": "Field corrected successfully",
        "field_id": field.id,
        "effective_value": get_effective_field_value(field),
        "is_overridden": field.is_overridden,
    }


@router.post("/{document_id}/fields/{field_id}/override")
def override_field(
    document_id: str,
    field_id: str,
    payload: FieldOverrideIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Overrides an extracted field value while preserving original_value in the audit ledger."""
    field = db.query(ExtractedField).filter(
        ExtractedField.id == field_id,
        ExtractedField.document_id == document_id,
        ExtractedField.deleted_at.is_(None),
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    if field.document and field.document.case and field.document.case.status and field.document.case.status.lower() in ["approved", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit case is locked ({field.document.case.status.title()}). Field overrides are prohibited on locked cases.",
        )

    old_effective = get_effective_field_value(field)
    field.corrected_value = payload.corrected_value
    field.is_overridden = True
    field.overridden_by = current_user.id
    field.override_comment = payload.comment
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="FIELD_OVERRIDDEN",
        entity_type="extracted_field",
        entity_id=field.id,
        case_id=field.document.case_id if field.document else None,
        payload={
            "field_name": field.field_name,
            "previous_value": old_effective,
            "corrected_value": payload.corrected_value,
            "comment": payload.comment,
        },
    )

    return {
        "message": "Field corrected successfully",
        "field_id": field.id,
        "effective_value": get_effective_field_value(field),
        "is_overridden": True,
    }


@router.post("/{document_id}/fields/{field_id}/revert")
def revert_field(
    document_id: str,
    field_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Reverts an overridden field back to its original extracted value."""
    field = db.query(ExtractedField).filter(
        ExtractedField.id == field_id,
        ExtractedField.document_id == document_id,
        ExtractedField.deleted_at.is_(None),
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    if field.document and field.document.case and field.document.case.status and field.document.case.status.lower() in ["approved", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit case is locked ({field.document.case.status.title()}). Field overrides are prohibited on locked cases.",
        )

    reverted_value = field.corrected_value
    field.corrected_value = None
    field.is_overridden = False
    field.override_comment = None
    field.overridden_by = None
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="FIELD_OVERRIDE_REVERTED",
        entity_type="extracted_field",
        entity_id=field.id,
        case_id=field.document.case_id if field.document else None,
        payload={
            "field_name": field.field_name,
            "reverted_value": reverted_value,
            "original_extracted_value": field.extracted_value,
        },
    )

    return {
        "message": "Field reverted to original extracted value",
        "effective_value": get_effective_field_value(field),
        "is_overridden": False,
    }


@router.post("/{document_id}/fields")
def add_manual_field(
    document_id: str,
    payload: FieldCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Allows an auditor to manually add a missing field with comment."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    new_field = ExtractedField(
        document_id=doc.id,
        field_name=payload.field_name,
        original_text="[Added manually by auditor]",
        extracted_value=payload.extracted_value,
        corrected_value=payload.extracted_value,
        is_overridden=True,
        overridden_by=current_user.id,
        override_comment=payload.comment,
        confidence=1.0,
        source_page=payload.source_page,
        bbox=payload.bbox,
        extractor="manual",
        validation_status="valid",
    )
    db.add(new_field)
    db.commit()
    db.refresh(new_field)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="MANUAL_FIELD_ADDED",
        entity_type="extracted_field",
        entity_id=new_field.id,
        case_id=doc.case_id,
        payload={
            "field_name": new_field.field_name,
            "value": payload.extracted_value,
            "comment": payload.comment,
        },
    )

    return {"message": "Manual field added successfully", "field_id": new_field.id}


@router.post("/{document_id}/annotations")
def add_annotation(
    document_id: str,
    payload: AnnotationCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adds a bounding box highlight note on a document page."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    annot = DocumentAnnotation(
        document_id=doc.id,
        page=payload.page,
        bbox=payload.bbox,
        note=payload.note,
        finding_id=payload.finding_id,
        created_by=current_user.id,
    )
    db.add(annot)
    db.commit()
    db.refresh(annot)

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="ANNOTATION_ADDED",
        entity_type="document_annotation",
        entity_id=annot.id,
        case_id=doc.case_id,
        payload={"page": annot.page, "note": annot.note},
    )

    return {
        "id": annot.id,
        "page": annot.page,
        "bbox": annot.bbox,
        "note": annot.note,
        "created_at": annot.created_at,
    }


@router.delete("/{document_id}/annotations/{annotation_id}")
def delete_annotation(
    document_id: str,
    annotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-deletes a document annotation with audit logging."""
    annot = db.query(DocumentAnnotation).filter(
        DocumentAnnotation.id == annotation_id,
        DocumentAnnotation.document_id == document_id,
        DocumentAnnotation.deleted_at.is_(None),
    ).first()
    if not annot:
        raise HTTPException(status_code=404, detail="Annotation not found")

    annot.deleted_at = datetime.now(timezone.utc)
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="ANNOTATION_DELETED",
        entity_type="document_annotation",
        entity_id=annot.id,
        case_id=annot.document.case_id if annot.document else None,
        payload={"page": annot.page},
    )

    return {"message": "Annotation deleted successfully"}


@router.post("/tabular-preview")
async def preview_tabular(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Parses first 10 rows and auto-detects column mapping for preview."""
    content = await file.read()
    res = parse_tabular_content(
        file_bytes=content,
        mime_type=file.content_type or "text/csv",
        limit=10,
    )
    return res


@router.post("/{document_id}/tabular-import")
def import_tabular(
    document_id: str,
    payload: TabularImportIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer", "senior_auditor", "auditor"])),
):
    """Imports CSV/XLSX rows into the transactions table using the confirmed column mapping."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = storage_service.read_file_bytes(doc.stored_filename, case_id=doc.case_id)

    res = parse_tabular_content(
        file_bytes=content,
        mime_type=doc.mime_type,
        custom_mapping=payload.mapping,
    )

    # Idempotent re-import: delete existing transactions from this document
    db.query(Transaction).filter(Transaction.source_document_id == doc.id).delete()

    created_count = 0
    case_scheme = doc.case.scheme_name if doc.case and doc.case.scheme_name else "General Scheme"
    for t in res["transactions"]:
        txn = Transaction(
            case_id=doc.case_id,
            source_document_id=doc.id,
            voucher_no=t["voucher_no"],
            transaction_date=datetime.fromisoformat(t["transaction_date"]).date(),
            amount=t["amount"],
            debit=t["debit"],
            credit=t["credit"],
            balance=t["balance"],
            scheme_name=case_scheme,
            payment_mode="Electronic",
            description=t["description"],
            row_number=t["row_number"],
        )
        db.add(txn)
        created_count += 1

    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="TABULAR_DATA_IMPORTED",
        entity_type="document",
        entity_id=doc.id,
        case_id=doc.case_id,
        payload={"rows_imported": created_count, "mapping": payload.mapping},
    )

    return {
        "message": f"Successfully imported {created_count} transactions.",
        "imported_rows": created_count,
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["administrator", "audit_officer"])),
):
    """Soft-deletes a document and records action in audit trail."""
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.deleted_at = datetime.now(timezone.utc)
    db.commit()

    log_activity(
        db=db,
        actor_id=current_user.id,
        action="DOCUMENT_DELETED",
        entity_type="document",
        entity_id=doc.id,
        case_id=doc.case_id,
        payload={"filename": doc.original_filename},
    )

    return {"message": "Document deleted successfully"}
