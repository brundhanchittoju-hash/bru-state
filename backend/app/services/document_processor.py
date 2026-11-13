import os
import json
import logging
import shutil
import tempfile
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document, DocumentVersion, ExtractedField
from app.models.audit_case import AuditCase
from app.models.financial import Transaction
from app.models.system import Job
from app.services.audit_trail import log_activity
from app.services.storage import storage_service
from app.services.extraction import (
    classify_document_text,
    extract_fields_from_text,
    extract_pdf_pages_and_thumbnails,
    extract_image_page,
    parse_tabular_content,
)

logger = logging.getLogger(__name__)


def process_document_pipeline(db: Session, document_id: str, job_id: Optional[str] = None) -> bool:
    """
    Executes the end-to-end extraction and classification pipeline for a document.
    Updates the document status, versions, extracted fields, and audit trail.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not doc:
        logger.error(f"Document {document_id} not found for processing")
        return False

    job = db.query(Job).filter(Job.id == job_id).first() if job_id else None

    try:
        # Mark Document and Job as processing
        doc.status = "processing"
        if job:
            job.status = "processing"
            job.progress = 20
        db.commit()

        # Update case status to 'processing' while jobs run
        audit_case = db.query(AuditCase).filter(AuditCase.id == doc.case_id).first()
        if audit_case and audit_case.status in ["draft", "documents_uploaded"]:
            audit_case.status = "processing"
            db.commit()

        # Resolve physical file path (handles local file or downloads from Supabase to a temp file and deletes it afterwards)
        with storage_service.get_local_file_path(doc.stored_filename, case_id=doc.case_id) as file_path:
            # Set up thumbnail output directory
            temp_thumb_dir = None
            if storage_service.is_supabase:
                temp_thumb_dir = tempfile.mkdtemp(prefix="thumbnails_")
                thumbnail_dir = temp_thumb_dir
            else:
                thumbnail_dir = os.path.join(settings.STORAGE_DIR, "thumbnails")
                os.makedirs(thumbnail_dir, exist_ok=True)

            try:
                mime = doc.mime_type.lower()
                extracted_fields_data = []
                doc_type = doc.document_type or "Unknown"
                doc_conf = 0.0
                doc_keywords = []
                extractor_used = "text_layer"
                page_count = 1

                if "pdf" in mime:
                    # 1. PDF Pipeline: text layer with word coordinates and thumbnails
                    pdf_result = extract_pdf_pages_and_thumbnails(
                        pdf_path=file_path,
                        output_thumbnail_dir=thumbnail_dir,
                        doc_id=doc.id,
                        min_text_threshold=50,
                    )
                    page_count = pdf_result["page_count"]
                    full_text = pdf_result["full_text"]
                    extractor_used = "ocr" if pdf_result["ocr_triggered"] and pdf_result["tesseract_available"] else "text_layer"

                    # 2. 13-Class Classification
                    class_res = classify_document_text(full_text)
                    doc_type = class_res["document_type"]
                    doc_conf = class_res["confidence"]
                    doc_keywords = class_res["matched_keywords"]

                    # 3. Field Extraction
                    extracted_fields_data = extract_fields_from_text(
                        pages_text=pdf_result["pages"],
                        document_type=doc_type,
                        ocr_mode=(extractor_used == "ocr"),
                    )

                elif "image" in mime:
                    # Image Pipeline (JPG, PNG)
                    img_result = extract_image_page(
                        image_path=file_path,
                        output_thumbnail_dir=thumbnail_dir,
                        doc_id=doc.id,
                    )
                    extractor_used = img_result["pages"][0]["extractor"]
                    full_text = img_result["full_text"]

                    class_res = classify_document_text(full_text)
                    doc_type = class_res["document_type"]
                    doc_conf = class_res["confidence"]
                    doc_keywords = class_res["matched_keywords"]

                    extracted_fields_data = extract_fields_from_text(
                        pages_text=img_result["pages"],
                        document_type=doc_type,
                        ocr_mode=True,
                    )

                elif "sheet" in mime or "excel" in mime or "csv" in mime or mime.endswith("csv"):
                    # Tabular Pipeline (CSV / Excel)
                    with open(file_path, "rb") as f:
                        content_bytes = f.read()
                    tab_res = parse_tabular_content(file_bytes=content_bytes, mime_type=mime)
                    page_count = 1
                    extractor_used = "rule_parser"
                    doc_type = "Bank Statement" if "bank" in doc.original_filename.lower() else "Ledger"
                    doc_conf = tab_res["confidence"]
                    doc_keywords = [f"Auto-mapped {len(tab_res['mapping'])} columns"]

                    # If auto-mapping was confident, insert parsed rows into transactions table
                    if tab_res["confidence"] >= 0.70 and tab_res["transactions"]:
                        # Idempotent re-import: clear previous transactions from this document
                        db.query(Transaction).filter(Transaction.source_document_id == doc.id).delete()
                        for t in tab_res["transactions"]:
                            txn = Transaction(
                                case_id=doc.case_id,
                                source_document_id=doc.id,
                                voucher_no=t["voucher_no"],
                                transaction_date=datetime.fromisoformat(t["transaction_date"]).date(),
                                amount=t["amount"],
                                debit=t["debit"],
                                credit=t["credit"],
                                balance=t["balance"],
                                scheme_name=audit_case.scheme_name if audit_case and audit_case.scheme_name else "General Scheme",
                                payment_mode="Electronic",
                                description=t["description"],
                                row_number=t["row_number"],
                            )
                            db.add(txn)

                # If in supabase mode, upload all generated thumbnails to Supabase bucket
                if storage_service.is_supabase and temp_thumb_dir and os.path.exists(temp_thumb_dir):
                    for t_file in os.listdir(temp_thumb_dir):
                        t_path = os.path.join(temp_thumb_dir, t_file)
                        with open(t_path, "rb") as tf:
                            storage_service.upload_bytes(f"thumbnails/{t_file}", tf.read(), content_type="image/png")
            finally:
                if temp_thumb_dir and os.path.exists(temp_thumb_dir):
                    try:
                        shutil.rmtree(temp_thumb_dir)
                    except Exception:
                        pass

        if job:
            job.progress = 70
            db.commit()

        # Save Extracted Fields into Database
        # Clean existing fields for this document to avoid duplicates on re-process
        db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
        for f_item in extracted_fields_data:
            field_rec = ExtractedField(
                document_id=doc.id,
                field_name=f_item["field_name"],
                original_text=f_item["original_text"],
                extracted_value=f_item["extracted_value"],
                confidence=f_item["confidence"],
                source_page=f_item["source_page"],
                bbox=f_item["bbox"],
                extractor=f_item["extractor"],
                validation_status=f_item["validation_status"],
                validation_message=f_item["validation_message"],
            )
            db.add(field_rec)

        # Update Document and current DocumentVersion record
        doc.status = "processed"
        doc.page_count = page_count
        doc.document_type = doc_type
        doc.classification_confidence = doc_conf
        doc.classification_keywords = json.dumps(doc_keywords)
        doc.extractor_used = extractor_used
        doc.processing_error = None

        # Check for extracted invoice/document date
        date_field = next((f for f in extracted_fields_data if f["field_name"] in ["invoice_date", "document_date"]), None)
        if date_field and date_field.get("extracted_value"):
            try:
                doc.document_date = datetime.fromisoformat(date_field["extracted_value"]).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Update latest version record
        latest_ver = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )
        if latest_ver:
            latest_ver.document_type = doc_type
            latest_ver.classification_confidence = doc_conf

        # Update AuditCase status to 'documents_uploaded' once done
        if audit_case:
            audit_case.status = "documents_uploaded"

        # Complete job
        if job:
            job.status = "completed"
            job.progress = 100
            job.error_message = None

        db.commit()

        # Log completion to Cryptographic Audit Trail
        log_activity(
            db=db,
            actor_id=doc.uploader_id,
            action="DOCUMENT_PROCESSED",
            entity_type="document",
            entity_id=doc.id,
            case_id=doc.case_id,
            payload={
                "document_type": doc_type,
                "confidence": doc_conf,
                "fields_extracted": len(extracted_fields_data),
                "extractor_used": extractor_used,
            },
        )
        return True

    except Exception as exc:
        db.rollback()
        logger.exception(f"Document processing failed for {document_id}: {exc}")
        doc.status = "failed"
        doc.processing_error = str(exc)
        if job:
            job.status = "failed"
            job.error_message = str(exc)
        db.commit()

        log_activity(
            db=db,
            actor_id=doc.uploader_id,
            action="DOCUMENT_PROCESSING_FAILED",
            entity_type="document",
            entity_id=doc.id,
            case_id=doc.case_id,
            payload={"error": str(exc)},
        )
        return False
