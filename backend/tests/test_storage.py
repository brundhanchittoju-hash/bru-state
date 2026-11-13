import io
from app.core.config import settings
from app.models.audit_case import AuditCase
from app.services.storage import compute_sha256


# Valid 1-pixel PNG file bytes with proper magic header
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Valid minimal PDF header
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\nxref\n0 1\n0000000000 65535 f \ntrailer<</Size 1/Root 1 0 R>>\nstartxref\n50\n%%EOF"


def get_demo_case_id(db_session):
    case = db_session.query(AuditCase).first()
    return case.id


def test_valid_upload_and_download(client, db_session, auth_tokens):
    case_id = get_demo_case_id(db_session)
    hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    files = {"file": ("receipt.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
    data = {"case_id": case_id, "title": "Gram Panchayat Receipt Voucher", "document_type": "voucher"}

    res = client.post("/api/documents/upload", files=files, data=data, headers=hdr)
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["title"] == "Gram Panchayat Receipt Voucher"
    assert doc_data["sha256_hash"] == compute_sha256(VALID_PNG_BYTES)

    # Test download
    doc_id = doc_data["id"]
    dl_res = client.get(f"/api/documents/{doc_id}/download", headers=hdr)
    assert dl_res.status_code == 200
    assert compute_sha256(dl_res.content) == doc_data["sha256_hash"]


def test_bad_extension_rejection(client, db_session, auth_tokens):
    case_id = get_demo_case_id(db_session)
    hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    files = {"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")}
    data = {"case_id": case_id}

    res = client.post("/api/documents/upload", files=files, data=data, headers=hdr)
    assert res.status_code == 400
    assert "not permitted" in res.json()["detail"]


def test_mismatched_mime_rejection(client, db_session, auth_tokens):
    case_id = get_demo_case_id(db_session)
    hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # Named .pdf but containing Windows executable header (magic bytes spoofing)
    spoofed_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    files = {"file": ("invoice.pdf", io.BytesIO(spoofed_bytes), "application/pdf")}
    data = {"case_id": case_id}

    res = client.post("/api/documents/upload", files=files, data=data, headers=hdr)
    assert res.status_code == 400
    assert "MIME type" in res.json()["detail"]


def test_oversize_rejection(client, db_session, auth_tokens, monkeypatch):
    case_id = get_demo_case_id(db_session)
    hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    # Temporarily set max size to 100 bytes for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)

    large_content = VALID_PNG_BYTES * 10
    files = {"file": ("large_document.png", io.BytesIO(large_content), "image/png")}
    data = {"case_id": case_id}

    res = client.post("/api/documents/upload", files=files, data=data, headers=hdr)
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"]


def test_duplicate_checksum_and_versioning(client, db_session, auth_tokens):
    case_id = get_demo_case_id(db_session)
    hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}

    pdf_bytes = VALID_PDF_BYTES + b"unique_v1_marker"
    files1 = {"file": ("tender_document.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data1 = {"case_id": case_id, "title": "Tender Document"}

    # First upload succeeds
    res1 = client.post("/api/documents/upload", files=files1, data=data1, headers=hdr)
    assert res1.status_code == 201
    doc1 = res1.json()

    # Second upload of the identical content to the same case triggers 409 Conflict
    files2 = {"file": ("tender_document_duplicate.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res2 = client.post("/api/documents/upload", files=files2, data=data1, headers=hdr)
    assert res2.status_code == 409
    err = res2.json()["detail"]
    assert err["code"] == "DUPLICATE_CHECKSUM"
    assert err["existing_document_id"] == doc1["id"]

    # Uploading as a new version succeeds
    files3 = {"file": ("tender_document_v2.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data_v2 = {"case_id": case_id, "as_new_version_of": doc1["id"]}
    res3 = client.post("/api/documents/upload", files=files3, data=data_v2, headers=hdr)
    assert res3.status_code == 201
