import os
import glob
import httpx

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
SEED_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_FILES_DIR = os.path.join(SEED_DIR, "sample_files")


def upload_all_samples():
    print(f"Connecting to {BASE_URL} to authenticate...")
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Login as senior auditor
        login_res = client.post(
            "/api/auth/login",
            json={
                "email": "senior.auditor@stateaudit.kar.gov.in",
                "password": "SeniorPassword@2024",
            },
        )
        if login_res.status_code != 200:
            print(f"[FAIL] Login failed: {login_res.text}")
            return False

        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get demo case ID
        cases_res = client.get("/api/cases", headers=headers)
        if cases_res.status_code != 200 or not cases_res.json():
            print(f"[FAIL] Could not retrieve cases: {cases_res.text}")
            return False

        case_id = cases_res.json()[0]["id"]
        case_no = cases_res.json()[0]["case_number"]
        print(f"[OK] Found target case: {case_no} ({case_id})")

        # 3. Upload each sample file with sync_process=True
        files = sorted(glob.glob(os.path.join(SAMPLE_FILES_DIR, "*.*")))
        print(f"Found {len(files)} sample files to upload...")

        success_count = 0
        for fpath in files:
            fname = os.path.basename(fpath)
            _, ext = os.path.splitext(fname)
            mime_map = {
                ".pdf": "application/pdf",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".csv": "text/csv",
                ".png": "image/png",
                ".jpg": "image/jpeg",
            }
            mime = mime_map.get(ext.lower(), "application/octet-stream")

            with open(fpath, "rb") as f:
                file_bytes = f.read()

            upload_res = client.post(
                "/api/documents/upload",
                headers=headers,
                data={
                    "case_id": case_id,
                    "title": f"DEMO - {fname}",
                    "sync_process": "true",
                },
                files={
                    "file": (fname, file_bytes, mime),
                },
            )

            if upload_res.status_code in [200, 201]:
                doc_data = upload_res.json()
                print(f"  [OK] Uploaded & Processed '{fname}': Type={doc_data.get('document_type')} (Confidence={int((doc_data.get('classification_confidence') or 0)*100)}%)")
                success_count += 1
            elif upload_res.status_code == 409:
                print(f"  [SKIP] '{fname}' already exists in case (duplicate checksum)")
                success_count += 1
            else:
                print(f"  [FAIL] Failed to upload '{fname}': {upload_res.status_code} {upload_res.text}")

        print(f"\n[DONE] Successfully processed {success_count}/{len(files)} sample documents into case {case_no}!")
        return True


if __name__ == "__main__":
    upload_all_samples()
