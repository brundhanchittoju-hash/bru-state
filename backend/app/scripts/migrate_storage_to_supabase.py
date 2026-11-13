"""
One-time, idempotent migration script to upload existing local files from /storage
to the private Supabase Storage bucket 'audit-documents' under UUID names,
and update stored database paths.

Supports:
  --dry-run       Preview actions without uploading or committing DB updates
  --storage-dir   Override path to local storage directory

Usage:
  python -m app.scripts.migrate_storage_to_supabase --dry-run
  python -m app.scripts.migrate_storage_to_supabase
"""

import argparse
import os
import re
import sys
import uuid
from typing import Optional, Set

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentVersion
from app.models.report import ReportVersion
from app.services.storage import SupabaseStorageClient, compute_sha256

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(\.[a-zA-Z0-9]+)?$",
    re.IGNORECASE,
)


def is_uuid_name(name: str) -> bool:
    """Checks if a filename is already formatted as a UUID or UUID.ext."""
    base = os.path.basename(name)
    return bool(UUID_REGEX.match(base))


STORAGE_SEARCH_DIRS = [
    os.path.abspath("backend/storage"),
    os.path.abspath("storage"),
    os.path.abspath(settings.STORAGE_DIR),
]


def resolve_local_file(filename: str, case_id: Optional[str] = None) -> Optional[str]:
    """Finds a file in local storage examining subdirectories and root."""
    if not filename:
        return None

    clean = filename.replace("\\", "/").replace("./storage/", "").replace("storage/", "")
    for s_dir in STORAGE_SEARCH_DIRS:
        if not os.path.exists(s_dir):
            continue
        candidates = [
            os.path.join(s_dir, case_id, filename) if case_id else None,
            os.path.join(s_dir, case_id, clean) if case_id else None,
            os.path.join(s_dir, filename),
            os.path.join(s_dir, clean),
            os.path.join(s_dir, "fixtures", filename),
            os.path.join(s_dir, "fixtures", clean),
            os.path.join(s_dir, "reports", filename),
            os.path.join(s_dir, "reports", clean),
            os.path.join(s_dir, "thumbnails", filename),
            os.path.join(s_dir, "thumbnails", clean),
        ]
        if os.path.isabs(filename) or filename.startswith("./") or filename.startswith(".\\"):
            candidates.insert(0, filename)

        for p in candidates:
            if p and os.path.exists(p) and os.path.isfile(p):
                return p
    return None


def fetch_all_existing_cloud_keys(client: SupabaseStorageClient) -> Set[str]:
    """Fetches all existing object keys from Supabase bucket in bulk for fast O(1) checks."""
    existing_keys: Set[str] = set()
    try:
        root_items = client.list_objects(prefix="")
        for it in root_items:
            name = it.get("name")
            if name:
                existing_keys.add(name)
        report_items = client.list_objects(prefix="reports")
        for it in report_items:
            name = it.get("name")
            if name:
                existing_keys.add(f"reports/{name}")
                existing_keys.add(name)
        thumb_items = client.list_objects(prefix="thumbnails")
        for it in thumb_items:
            name = it.get("name")
            if name:
                existing_keys.add(f"thumbnails/{name}")
                existing_keys.add(name)
    except Exception as e:
        print(f"  [WARN] Failed to prefetch existing cloud keys ({e}). Will check per-file.", flush=True)
    return existing_keys


def run_migration(dry_run: bool = False, storage_dir: Optional[str] = None):
    target_storage_dir = os.path.abspath(storage_dir or settings.STORAGE_DIR)
    if not os.path.exists(target_storage_dir):
        alt = os.path.abspath(os.path.join("backend", storage_dir or settings.STORAGE_DIR))
        if os.path.exists(alt):
            target_storage_dir = alt

    print("=" * 70, flush=True)
    print("STATE AUDIT AI — Supabase Storage Migration", flush=True)
    print(f"Mode: {'DRY RUN (No changes will be saved)' if dry_run else 'LIVE MIGRATION'}", flush=True)
    print(f"Source storage directory: {target_storage_dir}", flush=True)
    print(f"Target bucket: {settings.SUPABASE_STORAGE_BUCKET or 'audit-documents'}", flush=True)
    print("=" * 70, flush=True)

    # 1. Validate Supabase Configuration
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured in backend/.env", flush=True)
        sys.exit(1)

    client = SupabaseStorageClient(
        url=settings.SUPABASE_URL,
        service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
        bucket=settings.SUPABASE_STORAGE_BUCKET or "audit-documents",
    )

    if not dry_run:
        print("Ensuring Supabase storage bucket exists...", flush=True)
        if not client.ensure_bucket_exists():
            print("WARNING: Could not verify bucket creation. Proceeding with upload attempts.", flush=True)

    print("Prefetching existing files in bucket for fast idempotency checks...", flush=True)
    existing_cloud_keys = fetch_all_existing_cloud_keys(client)
    print(f"Found {len(existing_cloud_keys)} existing objects in Supabase bucket.", flush=True)

    db = SessionLocal()
    docs_uploaded = 0
    docs_updated = 0
    reports_uploaded = 0
    reports_updated = 0
    thumbs_uploaded = 0
    already_in_cloud = 0

    try:
        # ----------------------------------------------------------------------
        # 2. Migrate Documents and DocumentVersions
        # ----------------------------------------------------------------------
        print("\n--- Migrating Documents ---", flush=True)
        documents = db.query(Document).filter(Document.deleted_at.is_(None)).all()
        print(f"Found {len(documents)} active documents in database.", flush=True)

        for doc in documents:
            local_path = resolve_local_file(doc.stored_filename, case_id=doc.case_id)
            if not local_path:
                if doc.stored_filename in existing_cloud_keys or client.file_exists(doc.stored_filename):
                    already_in_cloud += 1
                else:
                    print(f"  [WARN] Document {doc.id} ({doc.title}): file missing locally and in cloud: {doc.stored_filename}", flush=True)
                continue

            with open(local_path, "rb") as f:
                content = f.read()

            _, ext = os.path.splitext(local_path)
            if not ext and doc.original_filename:
                _, ext = os.path.splitext(doc.original_filename)

            # Assign UUID name if not already UUID
            if is_uuid_name(doc.stored_filename):
                target_key = os.path.basename(doc.stored_filename)
            else:
                target_key = f"{uuid.uuid4()}{ext}"

            # Idempotency check: does file already exist in bucket?
            exists_in_bucket = (target_key in existing_cloud_keys) or (doc.stored_filename in existing_cloud_keys)
            if exists_in_bucket:
                already_in_cloud += 1
            else:
                if dry_run:
                    print(f"  [DRY RUN] Would upload {doc.original_filename} -> {target_key} ({len(content)} bytes)", flush=True)
                else:
                    client.upload_file(target_key, content, content_type=doc.mime_type)
                    existing_cloud_keys.add(target_key)
                    print(f"  [UPLOAD] {doc.original_filename} -> {target_key}", flush=True)
                docs_uploaded += 1

            # Update DB pointer if changed
            if target_key != doc.stored_filename:
                old_name = doc.stored_filename
                if dry_run:
                    print(f"  [DRY RUN] Would update Document {doc.id} stored_filename: {old_name} -> {target_key}", flush=True)
                else:
                    doc.stored_filename = target_key
                    for ver in doc.versions:
                        if ver.stored_filename == old_name:
                            ver.stored_filename = target_key
                docs_updated += 1

        # Check distinct DocumentVersion records
        doc_versions = db.query(DocumentVersion).all()
        for ver in doc_versions:
            if ver.stored_filename and not is_uuid_name(ver.stored_filename):
                local_path = resolve_local_file(ver.stored_filename)
                if local_path and os.path.exists(local_path):
                    with open(local_path, "rb") as f:
                        content = f.read()
                    _, ext = os.path.splitext(local_path)
                    target_key = f"{uuid.uuid4()}{ext}"
                    if target_key not in existing_cloud_keys:
                        if not dry_run:
                            client.upload_file(target_key, content)
                            existing_cloud_keys.add(target_key)
                            ver.stored_filename = target_key
                        docs_uploaded += 1
                        docs_updated += 1

        # ----------------------------------------------------------------------
        # 3. Migrate Statutory Reports
        # ----------------------------------------------------------------------
        print("\n--- Migrating Statutory Reports ---", flush=True)
        report_versions = db.query(ReportVersion).all()
        print(f"Found {len(report_versions)} report versions in database.", flush=True)

        for rv in report_versions:
            if not rv.file_path:
                continue

            local_path = resolve_local_file(rv.file_path)
            if not local_path:
                clean_key = rv.file_path.replace("\\", "/").lstrip("/")
                if clean_key in existing_cloud_keys:
                    already_in_cloud += 1
                else:
                    print(f"  [WARN] ReportVersion {rv.id}: file missing locally and in cloud: {rv.file_path}", flush=True)
                continue

            with open(local_path, "rb") as f:
                content = f.read()

            target_key = f"reports/{uuid.uuid4()}.pdf"
            if dry_run:
                print(f"  [DRY RUN] Would upload ReportVersion {rv.id} -> {target_key} ({len(content)} bytes)", flush=True)
            else:
                client.upload_file(target_key, content, content_type="application/pdf")
                existing_cloud_keys.add(target_key)
                print(f"  [UPLOAD] ReportVersion {rv.id} -> {target_key}", flush=True)
                rv.file_path = target_key
                rv.pdf_storage_path = target_key
            reports_uploaded += 1
            reports_updated += 1

        # ----------------------------------------------------------------------
        # 4. Migrate Thumbnails
        # ----------------------------------------------------------------------
        print("\n--- Migrating Page Thumbnails ---", flush=True)
        thumb_dir = None
        for s in STORAGE_SEARCH_DIRS:
            candidate = os.path.join(s, "thumbnails")
            if os.path.exists(candidate):
                thumb_dir = candidate
                break

        if thumb_dir and os.path.exists(thumb_dir):
            thumb_files = [f for f in os.listdir(thumb_dir) if f.endswith(".png")]
            print(f"Found {len(thumb_files)} thumbnail images on disk.", flush=True)

            for t_file in thumb_files:
                thumb_path = os.path.join(thumb_dir, t_file)
                thumb_key = f"thumbnails/{t_file}"

                if thumb_key in existing_cloud_keys:
                    already_in_cloud += 1
                    continue

                with open(thumb_path, "rb") as f:
                    t_bytes = f.read()

                if dry_run:
                    print(f"  [DRY RUN] Would upload thumbnail {t_file} -> {thumb_key}", flush=True)
                else:
                    client.upload_file(thumb_key, t_bytes, content_type="image/png")
                    existing_cloud_keys.add(thumb_key)
                thumbs_uploaded += 1
        else:
            print("No local thumbnail directory found.", flush=True)

        # Commit DB updates
        if not dry_run:
            db.commit()
            print("\n[SUCCESS] Database paths updated and committed successfully.", flush=True)
        else:
            db.rollback()
            print("\n[DRY RUN COMPLETE] Zero database mutations performed.", flush=True)

        print("\n" + "=" * 70, flush=True)
        print("MIGRATION SUMMARY", flush=True)
        print(f"  Mode:                {'DRY RUN' if dry_run else 'LIVE'}", flush=True)
        print(f"  Documents uploaded:  {docs_uploaded}", flush=True)
        print(f"  Documents updated:   {docs_updated}", flush=True)
        print(f"  Reports uploaded:    {reports_uploaded}", flush=True)
        print(f"  Reports updated:     {reports_updated}", flush=True)
        print(f"  Thumbnails uploaded: {thumbs_uploaded}", flush=True)
        print(f"  Already in Supabase: {already_in_cloud}", flush=True)
        print("=" * 70, flush=True)

    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] Migration aborted due to exception: {exc}", flush=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local storage files to Supabase Storage.")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration without modifying storage or database")
    parser.add_argument("--storage-dir", type=str, default=None, help="Custom local storage directory")
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run, storage_dir=args.storage_dir)
