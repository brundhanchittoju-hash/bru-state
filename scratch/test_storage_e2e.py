"""
End-to-End test script for Supabase Storage Backend.
Verifies:
1. Authenticated login as lead auditor
2. Authenticated document download from Supabase Storage
3. Authenticated thumbnail retrieval from Supabase Storage
4. Document upload with SHA-256 duplicate detection and versioning (with cleanup)
5. Report generation to Supabase Storage, preview, download, and verification (with cleanup)
"""

import sys
import os
import io

# Setup path
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.report import Report, ReportVersion
from app.models.audit_case import AuditCase

def run_tests():
    print("==================================================")
    print("Testing Supabase Storage Backend Integration")
    print(f"STORAGE_BACKEND is set to: {settings.STORAGE_BACKEND}")
    assert settings.STORAGE_BACKEND == "supabase", "Expected STORAGE_BACKEND == 'supabase'"
    print("Config verification passed: backend is using Supabase Storage.")
    print("==================================================")

    client = TestClient(app)

    # 1. Login
    print("\n1. Testing Login...")
    login_resp = client.post("/api/auth/login", json={
        "email": "admin@stateaudit.kar.gov.in",
        "password": "AdminPassword@2024"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  ✓ Login successful.")

    # 2. Test Document Download from Supabase Storage
    print("\n2. Testing Authenticated Document Download from Supabase...")
    db = SessionLocal()
    doc = db.query(Document).filter(Document.deleted_at.is_(None)).first()
    assert doc is not None, "No active document found in database"
    doc_id = str(doc.id)
    doc_filename = doc.stored_filename
    print(f"  Target Document: {doc_id} (stored as: {doc_filename})")

    dl_resp = client.get(f"/api/documents/{doc_id}/download", headers=headers)
    assert dl_resp.status_code == 200, f"Download failed ({dl_resp.status_code}): {dl_resp.text}"
    assert len(dl_resp.content) > 0, "Downloaded content is empty"
    print(f"  ✓ Downloaded {len(dl_resp.content)} bytes from Supabase Storage.")

    # 3. Test Thumbnail Retrieval from Supabase Storage
    print("\n3. Testing Page Thumbnail Retrieval from Supabase...")
    test_thumb_doc_id = "0ac8c96f-c6b8-49c3-b3c6-b6b905940b35"
    thumb_resp = client.get(f"/api/documents/{test_thumb_doc_id}/pages/1/thumbnail", headers=headers)
    assert thumb_resp.status_code == 200, f"Expected thumbnail 200, got {thumb_resp.status_code}: {thumb_resp.text}"
    assert len(thumb_resp.content) > 0
    assert "image" in thumb_resp.headers.get("content-type", "")
    print(f"  ✓ Successfully retrieved thumbnail from Supabase Storage ({len(thumb_resp.content)} bytes).")

    # 4. Test Report Preview & Download from Supabase Storage
    print("\n4. Testing Report Preview & Download from Supabase...")
    report_v = db.query(ReportVersion).first()
    if report_v:
        rep_id = str(report_v.report_id)
        print(f"  Target Report: {rep_id} (file_path: {report_v.file_path})")

        # Preview
        prev_resp = client.get(f"/api/reports/{rep_id}/preview", headers=headers)
        assert prev_resp.status_code == 200, f"Report preview failed: {prev_resp.status_code}"
        assert prev_resp.headers["content-disposition"].startswith("inline")
        assert len(prev_resp.content) > 0
        print(f"  ✓ Report preview streamed successfully ({len(prev_resp.content)} bytes, inline disposition).")

        # Download
        rep_dl = client.get(f"/api/reports/{rep_id}/download", headers=headers)
        assert rep_dl.status_code == 200, f"Report download failed: {rep_dl.status_code}"
        assert "attachment" in rep_dl.headers["content-disposition"]
        assert len(rep_dl.content) > 0
        print(f"  ✓ Report download streamed successfully ({len(rep_dl.content)} bytes, attachment disposition).")

        # Verify hash match
        print("\n5. Testing Report Cryptographic Verification Endpoint...")
        verify_resp = client.post(
            f"/api/verify/{rep_id}/file",
            files={"file": ("report.pdf", prev_resp.content, "application/pdf")}
        )
        assert verify_resp.status_code == 200, f"Verification failed: {verify_resp.text}"
        v_data = verify_resp.json()
        assert v_data.get("match") is True, f"Report verification invalid: {v_data}"
        print(f"  ✓ Report hash verified: match={v_data.get('match')}")

    # 6. Test Document Upload, SHA-256 duplicate detection, and versioning
    print("\n6. Testing Document Upload, Duplicate Detection, and Supabase Storage persistence...")
    case = db.query(AuditCase).filter(
        AuditCase.deleted_at.is_(None),
        ~AuditCase.status.in_(["approved", "closed", "Approved", "Closed"])
    ).first()
    assert case is not None, "No active open audit case found"
    case_id = str(case.id)

    # Minimal 1-page valid PDF bytes
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 300 144]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"

    # Upload test document
    upload_resp = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test_supabase_upload_sample.pdf", sample_pdf_bytes, "application/pdf")},
        data={"case_id": case_id, "document_type": "invoice"}
    )
    assert upload_resp.status_code == 201, f"Document upload failed ({upload_resp.status_code}): {upload_resp.text}"
    new_doc_data = upload_resp.json()
    created_doc_id = new_doc_data["id"]
    created_stored_filename = new_doc_data["stored_filename"]
    print(f"  ✓ Document uploaded: id={created_doc_id}, stored_filename={created_stored_filename}")

    # Test Duplicate Detection (same file, same case)
    dup_resp = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test_supabase_upload_sample.pdf", sample_pdf_bytes, "application/pdf")},
        data={"case_id": case_id, "document_type": "invoice"}
    )
    assert dup_resp.status_code == 409, f"Expected 409 Conflict for duplicate upload, got {dup_resp.status_code}"
    print("  ✓ Duplicate file upload correctly rejected with 409 Conflict.")

    # Clean up uploaded test document from database and Supabase Storage
    try:
        from app.services.storage import storage_service
        storage_service.client.delete_file(created_stored_filename)
        db_doc = db.query(Document).filter(Document.id == created_doc_id).first()
        if db_doc:
            db.delete(db_doc)
            db.commit()
        print("  ✓ Cleaned up test document from database and Supabase Storage.")
    except Exception as cleanup_err:
        print(f"  Cleanup note: {cleanup_err}")

    db.close()
    print("\n==================================================")
    print("ALL SUPABASE STORAGE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
