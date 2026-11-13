from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.common import ORMModel


class DocumentVersionOut(ORMModel):
    id: str
    document_id: str
    version_number: int
    stored_filename: str
    sha256_hash: str
    file_size: int
    document_type: Optional[str] = None
    classification_confidence: float = 0.0
    change_summary: Optional[str] = None
    created_by: str
    created_at: datetime


class ExtractedFieldOut(ORMModel):
    id: str
    document_id: str
    field_name: str
    original_text: Optional[str] = None
    extracted_value: Optional[str] = None
    corrected_value: Optional[str] = None
    effective_value: Optional[str] = None
    is_overridden: bool = False
    overridden_by: Optional[str] = None
    override_comment: Optional[str] = None
    confidence: float = 1.0
    source_page: int = 1
    bbox: Optional[str] = None
    extractor: str = "text_layer"
    validation_status: str = "not_checked"
    validation_message: Optional[str] = None
    extracted_at: datetime


class DocumentAnnotationOut(ORMModel):
    id: str
    document_id: str
    page: int
    bbox: Optional[str] = None
    note: str
    finding_id: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime


class DocumentOut(ORMModel):
    id: str
    case_id: str
    case_number: Optional[str] = None
    title: str
    original_filename: str
    stored_filename: str
    file_size: int
    mime_type: str
    sha256_hash: str
    document_type: Optional[str] = None
    status: str = "uploaded"
    page_count: int = 0
    current_version: int = 1
    classification_confidence: float = 0.0
    classification_keywords: Optional[str] = None
    extractor_used: Optional[str] = None
    processing_error: Optional[str] = None
    document_date: Optional[datetime] = None
    uploader_id: str
    uploader_name: Optional[str] = None
    created_at: datetime
    job_id: Optional[str] = None


class DocumentDetailOut(DocumentOut):
    versions: List[DocumentVersionOut] = []
    extracted_fields: List[ExtractedFieldOut] = []
    annotations: List[DocumentAnnotationOut] = []


class FieldOverrideIn(BaseModel):
    corrected_value: str = Field(..., min_length=1)
    comment: str = Field(..., min_length=3, description="Mandatory audit explanation for manual override")


class FieldCreateIn(BaseModel):
    field_name: str = Field(..., min_length=2, max_length=100)
    extracted_value: str = Field(..., min_length=1)
    source_page: int = Field(default=1, ge=1)
    bbox: Optional[str] = None
    comment: str = Field(..., min_length=3, description="Audit reason for manual field addition")


class ReclassifyIn(BaseModel):
    document_type: str = Field(..., min_length=2, max_length=100)
    comment: str = Field(..., min_length=3, description="Audit justification for reclassification")


class AnnotationCreateIn(BaseModel):
    page: int = Field(..., ge=1)
    bbox: Optional[str] = None  # JSON "[x0, y0, x1, y1]"
    note: str = Field(..., min_length=1, max_length=1000)
    finding_id: Optional[str] = None


class TabularImportIn(BaseModel):
    mapping: Dict[str, str] = Field(..., description="Column mapping e.g. {'date': 'Txn Date', 'debit': 'Dr'}")
