import hashlib
import io
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from typing import Generator, Optional, Tuple, Union

import filetype
import httpx
from fastapi import HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentVersion
from app.services.audit_trail import log_activity

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".csv", ".xlsx"}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/csv",
    "text/plain",  # CSV files are often identified as text/plain
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",  # XLSX files are internally zip archives
}


def ensure_storage_dir():
    """Ensures the local storage directory exists."""
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)


def validate_file(filename: str, content: bytes, reported_content_type: Optional[str] = None):
    """
    Validates file extension, size limit, and actual MIME type using magic numbers.
    """
    # 1. Size check
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb:.0f} MB",
        )

    # 2. Extension check
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 3. MIME magic bytes check
    kind = filetype.guess(content)
    detected_mime = kind.mime if kind else None

    # Handle text/csv special case (plain text doesn't have a binary magic header)
    if ext == ".csv":
        try:
            content[:1024].decode("utf-8")
            effective_mime = "text/csv"
        except UnicodeDecodeError:
            try:
                content[:1024].decode("latin-1")
                effective_mime = "text/csv"
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid CSV file: content cannot be decoded as text",
                )
    elif detected_mime:
        effective_mime = detected_mime
    else:
        # If magic number not matched, fallback to reported content type if allowed
        effective_mime = reported_content_type or "application/octet-stream"

    if effective_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File MIME type '{effective_mime}' is not permitted.",
        )

    return ext, effective_mime


def compute_sha256(content: bytes) -> str:
    """Computes hexadecimal SHA-256 checksum."""
    return hashlib.sha256(content).hexdigest()


class SupabaseStorageClient:
    """Client for Supabase Storage REST API."""

    def __init__(self, url: str, service_role_key: str, bucket: str = "audit-documents"):
        self.base_url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket
        self._headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apiKey": self.service_role_key,
        }

    def ensure_bucket_exists(self) -> bool:
        """Verifies or creates the target private bucket."""
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{self.base_url}/storage/v1/bucket/{self.bucket}", headers=self._headers)
            if resp.status_code == 200:
                return True
            if resp.status_code == 404:
                create_resp = client.post(
                    f"{self.base_url}/storage/v1/bucket",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={"id": self.bucket, "name": self.bucket, "public": False},
                )
                return create_resp.status_code in (200, 201)
            return False

    def upload_file(self, object_name: str, content: bytes, content_type: Optional[str] = None) -> str:
        """Uploads file content to the private Supabase Storage bucket."""
        clean_name = object_name.lstrip("/").replace("\\", "/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_name}"
        headers = {
            **self._headers,
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, content=content)
            if response.status_code not in (200, 201):
                logger.error(f"Supabase upload failed: status={response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to upload document to secure cloud storage: {response.text}",
                )
        return clean_name

    def download_file(self, object_name: str) -> bytes:
        """Downloads file bytes from private Supabase Storage bucket."""
        clean_name = object_name.lstrip("/").replace("\\", "/")
        urls = [
            f"{self.base_url}/storage/v1/object/authenticated/{self.bucket}/{clean_name}",
            f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_name}",
        ]
        with httpx.Client(timeout=60.0) as client:
            for u in urls:
                try:
                    resp = client.get(u, headers=self._headers)
                    if resp.status_code == 200:
                        return resp.content
                    if resp.status_code == 404:
                        continue
                    resp.raise_for_status()
                except Exception as e:
                    logger.debug(f"Error checking download URL {u}: {e}")
                    continue

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file not found in cloud storage",
        )

    def list_objects(self, prefix: str = "", limit: int = 1000) -> list:
        """Lists objects under a given prefix."""
        url = f"{self.base_url}/storage/v1/object/list/{self.bucket}"
        headers = {**self._headers, "Content-Type": "application/json"}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, json={"prefix": prefix, "limit": limit, "offset": 0})
            if resp.status_code == 200:
                return resp.json()
            return []

    def file_exists(self, object_name: str) -> bool:
        """Checks if a file exists in the bucket."""
        clean_name = object_name.lstrip("/").replace("\\", "/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_name}"
        with httpx.Client(timeout=5.0) as client:
            try:
                resp = client.get(url, headers={**self._headers, "Range": "bytes=0-0"})
                return resp.status_code in (200, 206)
            except Exception:
                return False

    def delete_file(self, object_name: str) -> bool:
        """Deletes an object from the bucket."""
        clean_name = object_name.lstrip("/").replace("\\", "/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.request(
                "DELETE",
                url,
                headers={**self._headers, "Content-Type": "application/json"},
                json={"prefixes": [clean_name]},
            )
            return resp.status_code == 200


class StorageService:
    def __init__(self):
        self._supabase_client: Optional[SupabaseStorageClient] = None

    @property
    def is_supabase(self) -> bool:
        return (settings.STORAGE_BACKEND or "local").lower().strip() == "supabase"

    @property
    def supabase_client(self) -> SupabaseStorageClient:
        if self._supabase_client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase credentials not configured in backend environment",
                )
            self._supabase_client = SupabaseStorageClient(
                url=settings.SUPABASE_URL,
                service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                bucket=settings.SUPABASE_STORAGE_BUCKET or "audit-documents",
            )
        return self._supabase_client

    @classmethod
    def save_file(
        cls,
        db: Session,
        case_id: str,
        upload_file: UploadFile,
        content: bytes,
        user_id: str,
        user_name: str,
        title: Optional[str] = None,
        document_type: Optional[str] = "voucher",
        as_new_version_of: Optional[str] = None,
    ) -> Tuple[Document, Optional[DocumentVersion]]:
        return storage_service._save_file_impl(
            db=db,
            case_id=case_id,
            upload_file=upload_file,
            content=content,
            user_id=user_id,
            user_name=user_name,
            title=title,
            document_type=document_type,
            as_new_version_of=as_new_version_of,
        )

    def _save_file_impl(
        self,
        db: Session,
        case_id: str,
        upload_file: UploadFile,
        content: bytes,
        user_id: str,
        user_name: str,
        title: Optional[str] = None,
        document_type: Optional[str] = "voucher",
        as_new_version_of: Optional[str] = None,
    ) -> Tuple[Document, Optional[DocumentVersion]]:
        """
        Saves an uploaded file to storage (local disk or Supabase bucket).
        Preserves SHA-256 duplicate detection, versioning, and cryptographic audit trail.
        """
        if not self.is_supabase:
            ensure_storage_dir()

        original_filename = upload_file.filename or "uploaded_document"
        ext, validated_mime = validate_file(
            original_filename,
            content,
            upload_file.content_type,
        )
        sha256_hash = compute_sha256(content)
        file_size = len(content)

        # Duplicate checksum check within this case
        existing_doc = (
            db.query(Document)
            .filter(
                Document.case_id == case_id,
                Document.sha256_hash == sha256_hash,
                Document.deleted_at.is_(None),
            )
            .first()
        )

        if existing_doc and not as_new_version_of:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Duplicate file detected with identical checksum in this audit case",
                    "code": "DUPLICATE_CHECKSUM",
                    "existing_document_id": existing_doc.id,
                    "existing_filename": existing_doc.original_filename,
                    "suggestion": "Upload as a new version or choose a different document",
                },
            )

        # UUID-based storage filename
        stored_filename = f"{uuid.uuid4()}{ext}"

        # Persist physical file
        if self.is_supabase:
            self.supabase_client.upload_file(
                object_name=stored_filename,
                content=content,
                content_type=validated_mime,
            )
        else:
            target_path = os.path.join(settings.STORAGE_DIR, stored_filename)
            with open(target_path, "wb") as f:
                f.write(content)

        if as_new_version_of:
            parent_doc = (
                db.query(Document)
                .filter(Document.id == as_new_version_of, Document.deleted_at.is_(None))
                .first()
            )
            if not parent_doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent document for versioning not found",
                )

            # Determine next version number
            latest_version = (
                db.query(DocumentVersion)
                .filter(DocumentVersion.document_id == parent_doc.id)
                .order_by(DocumentVersion.version_number.desc())
                .first()
            )
            next_version = (latest_version.version_number + 1) if latest_version else 2

            doc_version = DocumentVersion(
                document_id=parent_doc.id,
                version_number=next_version,
                stored_filename=stored_filename,
                sha256_hash=sha256_hash,
                file_size=file_size,
                change_summary=f"Updated version {next_version} uploaded",
                created_by=user_id,
            )
            parent_doc.stored_filename = stored_filename
            parent_doc.sha256_hash = sha256_hash
            parent_doc.file_size = file_size
            parent_doc.current_version = next_version
            parent_doc.status = "uploaded"

            db.add(doc_version)
            db.commit()
            db.refresh(parent_doc)

            log_activity(
                db=db,
                action="document:version_upload",
                entity_type="document_version",
                entity_id=doc_version.id,
                actor_id=user_id,
                actor_name=user_name,
                case_id=case_id,
                payload={
                    "document_id": parent_doc.id,
                    "version": next_version,
                    "sha256": sha256_hash,
                    "storage_backend": "supabase" if self.is_supabase else "local",
                },
            )
            return parent_doc, doc_version

        # New Document
        new_doc = Document(
            case_id=case_id,
            title=title or original_filename,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            mime_type=validated_mime,
            sha256_hash=sha256_hash,
            document_type=document_type,
            uploader_id=user_id,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # Create initial Version 1 record
        v1 = DocumentVersion(
            document_id=new_doc.id,
            version_number=1,
            stored_filename=stored_filename,
            sha256_hash=sha256_hash,
            file_size=file_size,
            change_summary="Initial upload",
            created_by=user_id,
        )
        db.add(v1)
        db.commit()

        log_activity(
            db=db,
            action="document:upload",
            entity_type="document",
            entity_id=new_doc.id,
            actor_id=user_id,
            actor_name=user_name,
            case_id=case_id,
            payload={
                "filename": original_filename,
                "file_size": file_size,
                "sha256": sha256_hash,
                "mime_type": validated_mime,
                "storage_backend": "supabase" if self.is_supabase else "local",
            },
        )

        return new_doc, v1

    def read_file_bytes(self, stored_name: str, case_id: Optional[str] = None) -> bytes:
        """
        Reads binary file bytes from configured backend with transparent fallback.
        """
        clean_name = stored_name.replace("\\", "/").lstrip("/")

        if self.is_supabase:
            try:
                return self.supabase_client.download_file(clean_name)
            except Exception as e:
                logger.debug(f"Cloud download failed for '{clean_name}', checking local disk fallback: {e}")

        # Local filesystem resolution
        candidates = []
        clean = stored_name.replace("\\", "/").replace("./storage/", "").replace("storage/", "")
        for base_dir in [settings.STORAGE_DIR, "backend/storage", "./backend/storage"]:
            if not os.path.exists(base_dir):
                continue
            if case_id:
                candidates.append(os.path.join(base_dir, case_id, stored_name))
                candidates.append(os.path.join(base_dir, case_id, clean))
            candidates.append(os.path.join(base_dir, stored_name))
            candidates.append(os.path.join(base_dir, clean))
            candidates.append(os.path.join(base_dir, "fixtures", stored_name))
            candidates.append(os.path.join(base_dir, "fixtures", clean))
            candidates.append(os.path.join(base_dir, "reports", stored_name))
            candidates.append(os.path.join(base_dir, "reports", clean))
        # Handle cases where stored_name is already a full or relative path
        if os.path.isabs(stored_name) or stored_name.startswith("./") or stored_name.startswith(".\\"):
            candidates.insert(0, stored_name)

        for path in candidates:
            if path and os.path.exists(path) and os.path.isfile(path):
                with open(path, "rb") as f:
                    return f.read()

        # If in local mode and not found locally, check supabase if configured
        if not self.is_supabase and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                return self.supabase_client.download_file(clean_name)
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical document file missing on storage server",
        )

    @contextmanager
    def get_local_file_path(
        self, stored_name: str, case_id: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Provides a valid local filesystem path for processing libraries (PyMuPDF, Tesseract).
        In Supabase mode, downloads to a temp file and securely unlinks it upon exit.
        """
        clean_name = stored_name.replace("\\", "/").lstrip("/")

        # Check if file exists locally first
        local_candidates = []
        if case_id:
            local_candidates.append(os.path.join(settings.STORAGE_DIR, case_id, stored_name))
        local_candidates.append(os.path.join(settings.STORAGE_DIR, stored_name))
        if os.path.isabs(stored_name) or stored_name.startswith("./") or stored_name.startswith(".\\"):
            local_candidates.insert(0, stored_name)

        for path in local_candidates:
            if os.path.exists(path) and os.path.isfile(path):
                yield path
                return

        # Not on local disk; download from Supabase to a temporary file
        content = self.read_file_bytes(stored_name, case_id=case_id)
        _, ext = os.path.splitext(stored_name)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name

        try:
            yield temp_path
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as exc:
                    logger.debug(f"Failed to delete temp file {temp_path}: {exc}")

    def stream_file(
        self,
        stored_name: str,
        case_id: Optional[str] = None,
        media_type: str = "application/octet-stream",
        filename: Optional[str] = None,
        disposition: str = "attachment",
    ) -> Response:
        """
        Streams a document file to authenticated callers.
        Never exposes public URLs or bypasses backend access control.
        """
        clean_filename = filename or os.path.basename(stored_name)

        if self.is_supabase:
            content = self.read_file_bytes(stored_name, case_id=case_id)
            return StreamingResponse(
                io.BytesIO(content),
                media_type=media_type,
                headers={"Content-Disposition": f'{disposition}; filename="{clean_filename}"'},
            )

        # Local storage mode: prefer FileResponse for high-performance zero-copy sendfile
        local_path = None
        candidates = []
        clean = stored_name.replace("\\", "/").replace("./storage/", "").replace("storage/", "")
        for base_dir in [settings.STORAGE_DIR, "backend/storage", "./backend/storage"]:
            if not os.path.exists(base_dir):
                continue
            if case_id:
                candidates.append(os.path.join(base_dir, case_id, stored_name))
                candidates.append(os.path.join(base_dir, case_id, clean))
            candidates.append(os.path.join(base_dir, stored_name))
            candidates.append(os.path.join(base_dir, clean))
            candidates.append(os.path.join(base_dir, "fixtures", stored_name))
            candidates.append(os.path.join(base_dir, "fixtures", clean))
        for p in candidates:
            if p and os.path.exists(p) and os.path.isfile(p):
                local_path = p
                break

        if not local_path:
            # Fallback reading bytes
            content = self.read_file_bytes(stored_name, case_id=case_id)
            return StreamingResponse(
                io.BytesIO(content),
                media_type=media_type,
                headers={"Content-Disposition": f'{disposition}; filename="{clean_filename}"'},
            )

        return FileResponse(
            path=local_path,
            media_type=media_type,
            filename=clean_filename,
        )

    def stream_thumbnail(self, document_id: str, page_num: int) -> Response:
        """Streams a rendered page thumbnail image."""
        thumb_key = f"thumbnails/{document_id}_p{page_num}.png"
        local_path = os.path.join(settings.STORAGE_DIR, "thumbnails", f"{document_id}_p{page_num}.png")

        if self.is_supabase:
            try:
                content = self.supabase_client.download_file(thumb_key)
                return Response(content=content, media_type="image/png")
            except Exception:
                if os.path.exists(local_path):
                    return FileResponse(path=local_path, media_type="image/png")
                raise HTTPException(status_code=404, detail="Thumbnail not generated or page not found")

        if os.path.exists(local_path):
            return FileResponse(path=local_path, media_type="image/png")

        # Try cloud fallback if in local mode but configured
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                content = self.supabase_client.download_file(thumb_key)
                return Response(content=content, media_type="image/png")
            except Exception:
                pass

        raise HTTPException(status_code=404, detail="Thumbnail not generated or page not found")

    def upload_bytes(self, key: str, content: bytes, content_type: Optional[str] = None) -> str:
        """Uploads raw binary content (e.g. generated reports, thumbnails) to the active backend."""
        clean_key = key.replace("\\", "/").lstrip("/")
        if self.is_supabase:
            return self.supabase_client.upload_file(clean_key, content, content_type=content_type)
        else:
            target_path = os.path.join(settings.STORAGE_DIR, clean_key)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(content)
            return target_path

    def stream_report(
        self,
        file_path_or_key: str,
        filename: str,
        disposition: str = "inline",
    ) -> Response:
        """Streams a statutory audit report PDF."""
        clean_key = file_path_or_key.replace("\\", "/").lstrip("/")

        # Check local disk existence first if path starts with local storage
        if os.path.exists(file_path_or_key) and os.path.isfile(file_path_or_key):
            return FileResponse(
                file_path_or_key,
                media_type="application/pdf",
                headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
            )

        # In supabase mode or if file path is a key, read via read_file_bytes
        try:
            content = self.read_file_bytes(clean_key)
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/pdf",
                headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Report PDF file not found in storage")

    @staticmethod
    def get_file_path(document: Document) -> str:
        """Legacy helper for local filesystem path compatibility."""
        target_path = os.path.join(settings.STORAGE_DIR, document.stored_filename)
        if not os.path.exists(target_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file missing on storage server",
            )
        return target_path


storage_service = StorageService()