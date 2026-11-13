# STATE AUDIT AI — Karnataka State Audit Department & Zilla Panchayat System

[![Phase 1 Status](https://img.shields.io/badge/Phase%201-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Phase 2 Status](https://img.shields.io/badge/Phase%202-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Phase 3 Status](https://img.shields.io/badge/Phase%203-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Phase 4 Status](https://img.shields.io/badge/Phase%204-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Phase 5 Status](https://img.shields.io/badge/Phase%205-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Phase 6 Status](https://img.shields.io/badge/Phase%206-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Full Seed Status](https://img.shields.io/badge/Full%20Seed-COMPLETE%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Final Acceptance](https://img.shields.io/badge/Final%20Acceptance-VERIFIED%20✓-0F9D9A?style=for-the-badge)](./CHECKLIST.md)
[![Database](https://img.shields.io/badge/Database-SQLite%20(Dev)%20%2F%20PostgreSQL%2015-0B1F3A?style=for-the-badge)](./DECISIONS.md)
[![Design Tokens](https://img.shields.io/badge/Palette-Navy%20%26%20Teal-0B1F3A?style=for-the-badge)](./frontend/src/styles/index.css)

**STATE AUDIT AI** is a production-grade, AI-assisted financial audit case management platform custom-built for the **Karnataka State Audit Department** and **Zilla Panchayat** audit directorates.

The platform is designed around strict statutory financial auditing standards, **human-in-the-loop oversight** (the system assists human auditors and never replaces them; automated findings are strictly labeled *"flagged for review"* or *"recommended for review"* and never *"fraud"*), cryptographic audit logging, and role-based governance across Panchayati Raj institutions.

---

## Architecture Overview

```
                                      ┌─────────────────────────────────────────┐
                                      │   React 18 + Vite + TypeScript Strict   │
                                      │   Tailwind CSS (Deep Navy & Vibrant Teal)│
                                      │   Light & Dark Mode • Cmd+K Menu        │
                                      └────────────────────┬────────────────────┘
                                                           │ HTTP / REST
                                                           ▼
                                      ┌─────────────────────────────────────────┐
                                      │     FastAPI (Python 3.12, Async API)    │
                                      │  Argon2 Password Hash • JWT Auth (HS256) │
                                      │  RBAC Matrix (Admin, Officer, Sr, Aud)  │
                                      │  Magic-Byte MIME Storage & Checksums    │
                                      └────────────────────┬────────────────────┘
                                                           │
                                ┌──────────────────────────┴──────────────────────────┐
                                ▼                                                     ▼
     ┌────────────────────────────────────┐                ┌────────────────────────────────────┐
     │   SQLAlchemy 2.0 (36 Core Tables)  │                │   Append-Only Cryptographic Ledger │
     │  SQLite Fallback / PostgreSQL 15   │                │   SHA-256 Hash Chained Records     │
     │  Alembic Migrations • Soft Deletes │                │   Public GET /api/audit-trail/verify│
     └────────────────────────────────────┘                └────────────────────────────────────┘
```

### Core Capabilities Implemented:

#### Phase 1: Foundation, Security & App Shell
1. **Complete 25-Table Schema**: All database models created with UUID primary keys, UTC timestamps, soft-delete (`deleted_at`), foreign keys with indexes, and CHECK constraints. Cleanly migrates via Alembic.
2. **Cryptographic Append-Only Activity Log**: Every state mutation is chained using:
   `SHA-256(prev_hash + sequence_id + ISO8601_UTC + actor_id + action + entity_type + entity_id + canonical_json(payload))`
   Genesis entry uses 64 zeros. Updates and deletes are blocked. Verified via `GET /api/audit-trail/verify`.
3. **Argon2 Auth & Brute-Force Lockout**: Password hashing via `argon2-cffi`, JWT access tokens (15m) + refresh tokens (7d), and automatic 15-minute account lockout after 5 consecutive failed attempts.
4. **Role-Based Access Control (RBAC)**: 4 roles enforced across backend routes and frontend UI (`Administrator`, `Audit Officer`, `Senior Auditor`, `Auditor`).
5. **Private Document Storage**: Files stored under `storage/<case_id>/<doc_uuid>.<ext>` with SHA-256 checksums, `python-magic` MIME validation, 25MB limits, and duplicate checksum detection per case.
6. **Karnataka Localization & Seed Data**: Seeded with 7 departments, 4 demo users, Karnataka terms, public holidays, and demo cases.
7. **Frontend App Shell**: React 18, Vite, TypeScript strict mode, Navy/Teal design system, Light/Dark modes, Topbar "Audit trail verified ✓" dialog, and persistent "DEMO DATA" badge.

#### Phase 2: Document Pipeline & Human-in-the-Loop Extraction
1. **Multi-Class Document Classifier**: Rules-based and keyword engine classifying 13 statutory document types (Bill, Voucher, Work Order, Sanction Order, Tender, Measurement Book, Completion Certificate, Utilization Certificate, Cash Book, Ledger, Bank Statement, Quotation, Supporting Document) supporting English and Kannada headers.
2. **Statutory Field Extractor & Normalized Bounding Boxes**: Extracts 20 statutory fields (`gstin`, `pan`, `ifsc_code`, `total_amount`, `taxable_amount`, `cgst_amount`, `sgst_amount`, `bill_number`, `voucher_number`, etc.) with 0.0–1.0 resolution-independent bounding boxes.
3. **Indian Currency & Statutory Validators**: Indian comma groupings (Lakhs/Crores), Dr/Cr notations, negative brackets, words-to-amount cross check, Indian dates (`DD/MM/YYYY`, `DD-MM-YYYY`), GSTIN Luhn Mod-36 validation, PAN structure, and IFSC codes.
4. **Tabular Register Parser**: CSV/XLSX synonym auto-mapping engine recognizing government register columns (`v_no`, `kpp_id`, `passed_amount`, `debit`, `dr`, `vendor_name`) with interactive 5-row preview and transaction batch ingestion.
5. **Split-Pane Side-by-Side Document Viewer**: Left pane renders high-resolution page canvas with interactive zoom (50%-250%), 90° clockwise rotation, and real-time bounding box highlight overlays; right pane renders confidence-coded statutory fields, raw text, and audit versions.
6. **Human-in-the-Loop Field Overrides**: Auditors can manually override extracted fields by supplying a mandatory justification. Recorded in the cryptographic ledger with full audit trail. Easily reversible with one click.
7. **Document Reclassification & Page Annotations**: Auditors can reclassify misclassified documents with justification notes or drop spatial sticky notes on document pages.
8. **Duplicate Hash Versioning Dialog**: Interactive collision handler when a document with identical SHA-256 is detected, offering one-click navigation to existing file or explicit re-versioning.

#### Phase 3: Financial Verification & Risk Engine
1. **Normalized Financial Records Layer**: Reconstructs unified ledger records (`FinancialRecord`) from extracted document fields and imported tabular transactions with deterministic, idempotent IDs.
2. **Payment Chain Linker**: Connects disbursement records across lifecycle stages (`Sanction Order` -> `Work Order` -> `Bill` -> `Voucher` -> `Bank Debit`). Disallow multiple counting: vouchers serve as the ground-truth disbursement records for total spend and vendor concentration calculations.
3. **RapidFuzz Fuzzy Vendor Resolution**: Normalizes vendor identities using token sort ratio ($\ge 88\%$). Ambiguous matches ($70-87\%$) are flagged for administrator human review in the `vendor_aliases` table.
4. **16 Statutory Verification Rules**: Implements KFC, KTPP Act 1999, and Karnataka Panchayati Raj Accounting Rules (R-001 Duplicate Payment, R-002 Split Tender, R-003 Missing Sanction, R-004 Sanction Excess, R-005 Tax Mismatch, R-006 Line Item Total Mismatch, R-007 Bank-Voucher Variance, R-008 Ineligible Tax Invoice, R-009 Stale Cheque / Delayed Presentation, R-010 Voucher Sequence Gap / Inversion, R-011 Missing Required Supporting Docs, R-012 Cash Payment Cap Exceeded [> ₹1,000], R-013 Vendor Concentration Alert [>= 40%], R-014 Split Purchase Clustering [< ₹5L], R-015 Round Amount Anomaly, R-016 Non-Working Day / March 31 Rush).
5. **7-Factor Weighted Risk Engine**: Computes normalized 0-100 risk score (Low 0-29, Medium 30-59, High 60-84, Critical 85-100) with a statutory floor override: any Critical finding clamps the score to $\ge 85$; any High finding clamps the score to $\ge 60$. Transparent mathematical formula modal.
6. **Idempotent Verification Runner**: Generates deterministic candidate fingerprints. Preserves human review decisions (`Confirmed`, `Dismissed`, `Under Review`, `Escalated`). Cleared findings are auto-resolved; underlying data changes set `data_changed_since_review = True` and write to the cryptographic activity log.
7. **Interactive Verification Workspace (`/verification`)**: Case selector, one-click verification run with simulated multi-step progress, radial risk gauge, 3-way reconciliation matrix with stage pill filters, 16-rule cards grid, top vendor concentration cards, slide-over finding detail drawer with evidence links, and threshold snapshot run history.
8. **Administrative Verification Settings**: 4 administrative tabs in `SettingsPage.tsx` enabling dynamic threshold tuning with mandatory change reasons, 7-factor risk weight sliders with live 100% sum validation guard, mandatory checklist management, and fuzzy vendor alias review.

#### Phase 4: Findings, Evidence, and Dual-Custody Review
1. **Findings Register & Multi-Filter Query Engine**: Sortable, paginated, server-side table with live database summary counters (by status, risk band, and total exposure). Free-text search, district, department, and risk band filtering.
2. **Per-User Saved Filter Presets**: Auditors can save customized multi-filter queries to the `saved_filters` table and recall them via interactive chip pills.
3. **Split-Pane Evidence Workspace (`/findings/:id`)**: High-resolution document viewer with synchronized bounding box highlights, source document switcher, and tabular row highlighting.
4. **8-Tab Explainability Dossier**: Extracted values with inline field overrides and re-verification triggers; side-by-side multi-stage comparison (Bill vs Voucher vs Ledger vs Bank); human-readable math calculation; factual reason with 7-factor risk bar breakdown; threaded reviewer notes; vertical cryptographic event timeline; referenced documents; and case-scoped related findings.
5. **Dual-Custody Maker-Checker Workflow**: Automatic transition to `Pending Approval` when an Auditor confirms/dismisses High or Critical findings. Dual sign-off required by Senior Auditor or Audit Officer. Strict backend block on self-approval (`403 Forbidden`).
6. **Case Immutability Lock**: Findings under `Approved` or `Closed` cases are locked against mutation (`423 Locked`). Reopening requires `Audit Officer` role and formal justification.
7. **Bulk Operations & CSV Export**: Bulk assignment to auditors, bulk clarification inquiries, and CSV export with SHA-256 hash chaining.

#### Phase 5: Cases, Dashboard, Search, and Analytics
1. **Full Audit Case Lifecycle & Blocker Gate**: 7-state administrative lifecycle (`draft` -> `documents_uploaded` -> `processing` -> `verification` -> `review` -> `approved` -> `closed`). Approval is strictly blocked if any unresolved High or Critical findings exist on the case. Reopening approved/closed cases requires Audit Officer role, mandatory justification, and generates immutable `case_versions` snapshots.
2. **Executive Dashboard (`/dashboard`)**: 12 live KPIs computed directly via SQL (zero hardcoding), priority review queue slide-over drawer with one-click navigation to evidence, calendar CRUD with `scheduled_events`, and real-time cryptographic activity stream.
3. **Audit Analytics & Intelligence (`/analytics`)**: 8 Recharts aggregations (Risk Distribution, Top Flagged Rules, Monthly Spend vs Flagged Exposure, District Exposure Heatmap, Status Pipeline, Vendor Concentration, Departmental Exposure, Confidence Breakdown) with accessible data table toggle and CSV export.
4. **Universal 7-Entity Search (`/search` & `⌘K`)**: Cross-entity search across Cases, Documents, Findings, Vendors, Rules, Vouchers, and Invoices with `Basic Search Mode (SQLite Fallback)` indicator.
5. **Vendors Directory & Dossier (`/vendors` & `/vendors/:id`)**: Searchable vendor directory with national PAN/GSTIN regex validity indicators, alias deduplication, aggregated voucher expenditure metrics, and linked statutory findings.

#### Phase 6: Statutory Audit Report Generator & Public Integrity Verification
1. **12-Section ReportLab PDF Engine**: Generates official audit reports conforming to Karnataka State Audit Department reporting standards (Executive Summary with AI template fallback, Case Particulars, Scope & Methodology, Audit Team & Dual-Custody Stamps, 7-Factor Risk Breakdown, Complete Findings Register, Financial Impact Ledger, Vendor Concentration, Payment Chain Evidence Traceability with PyMuPDF bbox snippet extracts, Mandatory Statutory Checklist, Auditor Observations & Recommendations, and Digital Sign-off & Verification Seal).
2. **Native Unicode Font & Indian Rupee (`₹`) Rendering**: Registered dynamic Unicode true-type fonts (`Segoe UI`, `Arial`, `Nirmala`) to render `\u20b9` glyph without font substitution errors.
3. **Vector QR Code & Dynamic Base URL**: Embedded built-in `reportlab.graphics.barcode.qr.QrCodeWidget` vector QR barcodes encoding the public verification URL (`${PUBLIC_BASE_URL}/verify/${report_id}`).
4. **Two-Pass `NumberedCanvas`**: Computes accurate total page count for "Page X of Y" statutory footer headers and stamps diagonal "DEMO DATA" security watermarks across every page.
5. **Pre-Generation Blocker Gate**: Prevents generation of "Final" audit reports if unresolved High or Critical findings exist on the case (Preliminary and Interim draft modes permitted).
6. **In-App Report Hub & Modals**: Case detail "Reports" tab and dedicated `/reports` register with interactive Preview Modal (embedded PDF iframe), Approval Modal (maker-checker validation), and Generation Modal.
7. **Zero-Knowledge Public Verification Portal (`/verify/:reportId`)**: Unauthenticated, rate-limited public portal providing statutory verification details without leaking sensitive vendor disclosures. Features an interactive in-memory file drag-and-drop hash checker that catches 1-byte file tampering in real time.

#### Full Seed Pipeline & Benchmark Dataset (`make seed` / `make reset-demo`)
1. **Deterministic Multi-Case Seeding**: Generates 5 realistic Karnataka audit cases across schemes (MGNREGA, PMAY-G, 15th FC Grants, JJM, SBM-G) and local body tiers (ZP, TP, GP), 50 real PDF/XLSX documents (including 6 scanned/skewed pages with noise and rotation), 21 statutory findings across all risk bands and states, 10 report versions, 6 users, and 15 vendors.
2. **Ground Truth Benchmark (`seed_ground_truth.json`)**: 14 intentional, cross-linked anomalies benchmarking R-001 through R-016 with 100% precision and recall, alongside a 100% clean case baseline (`CAS-2024-KAL-005` with 0 high/critical findings).

#### Final Acceptance & Hardening
1. **Two-Pass Consecutive Scripted Headless Acceptance E2E**: Playwright end-to-end acceptance test suite (`final_acceptance.spec.ts`) executed twice consecutively with 100% pass rate in headless mode without state cleanup between runs.
2. **Security & Parameterization Audit**: 100% parameterization verified across all SQL queries (0 string concatenations), zero occurrences of banned accusatory terminology, rate-limited public verification endpoints, and private storage file isolation.
3. **Performance Benchmarking**: Sub-40ms response latencies across all core database queries on seeded dataset (target < 300ms).

---

## Demo Accounts (Local Development Only)

> [!NOTE]
> **Local Development Only**: Demo accounts are provided strictly for local development, interface evaluation, and automated testing when `ENVIRONMENT=development` and `VITE_ENABLE_DEMO_LOGIN=true`. Demo passwords are not published in documentation or shipped in production. In local development, demo accounts are initialized via `python -m app.seed.seed_data`. In production environments, demo logins are disabled, demo accounts must be deactivated using `python -m app.scripts.manage_users deactivate-demo-users`, and administrator accounts are provisioned via `python -m app.scripts.manage_users create-admin <email>`.

| Role | Email | Allowed Permissions |
| :--- | :--- | :--- |
| **Administrator** | `admin@stateaudit.kar.gov.in` | User CRUD, System Settings, Audit Trail, Cases, Dual-Signoff |
| **Audit Officer** | `officer@stateaudit.kar.gov.in` | Case Reopen/Sign-off, Maker-Checker Dual-Approval, Cases, Verification |
| **Senior Auditor** | `senior.auditor@stateaudit.kar.gov.in` | Maker-Checker Dual-Approval, Bulk Assign, Findings Reopen, Workflow |
| **Auditor** | `auditor@stateaudit.kar.gov.in` | Sampling, Vouchers, Documents, Findings Creation & Confirmation |
| **Field Auditor 1**| `priya.nair@stateaudit.kar.gov.in` | Gram Panchayat field audit execution, document uploads |
| **Field Auditor 2**| `kavita.patil@stateaudit.kar.gov.in`| Taluk Panchayat field audit execution, document uploads |

### Statutory RBAC Endpoint Permissions Matrix

| Endpoint / Operation | Administrator | Audit Officer | Senior Auditor | Auditor | Enforcement Rule |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `GET /api/dashboard/stats`, `/calendar` | ✓ | ✓ | ✓ | ✓ | All authenticated roles |
| `POST, DELETE /api/dashboard/calendar` | ✓ | ✓ | ✓ | ✓ | All authenticated roles |
| `GET /api/analytics/aggregations` | ✓ | ✓ | ✓ | ✓ | All authenticated roles |
| `GET /api/search` (Multi-entity) | ✓ | ✓ | ✓ | ✓ | All authenticated roles |
| `GET /api/vendors`, `/vendors/{id}` | ✓ | ✓ | ✓ | ✓ | All authenticated roles |
| `POST /api/cases` (Create Case) | ✓ | ✓ | ✓ | ✓ | All authenticated roles |
| `PATCH /api/cases/{id}/status` | ✓ | ✓ | ✓ | — | High/Critical blocker gate enforced |
| `POST /api/cases/{id}/reopen` | ✓ | ✓ | — | — | Requires justification; creates snapshot |
| `POST /api/documents/upload` | ✓ | ✓ | ✓ | ✓ | Blocked on Locked cases (423) |
| `PATCH /api/documents/fields/{id}/override`| ✓ | ✓ | ✓ | ✓ | Blocked on Locked cases (423) |
| `POST /api/cases/{id}/verify` | ✓ | ✓ | ✓ | ✓ | Blocked on Locked cases (423) |
| `POST /api/findings/{id}/review` (Low/Med)| ✓ | ✓ | ✓ | ✓ | Direct confirm/dismiss |
| `POST /api/findings/{id}/review` (High/Crit)| Auto-Confirm | Auto-Confirm | Auto-Confirm | -> `Pending Approval` | Triggers dual-custody queue |
| Dual-Custody Approval / Rejection | ✓ | ✓ | ✓ | — | Strict self-approval block (403) |
| Reopen Confirmed/Dismissed Finding | ✓ | ✓ | ✓ | — | Requires justification comment |
| Bulk Assign (`/findings/bulk/assign`) | ✓ | ✓ | ✓ | — | Senior Auditor and above |
| Bulk Clarify (`/findings/bulk/clarify`)| ✓ | ✓ | ✓ | ✓ | All auditors |
| `POST /api/cases/{id}/reports/generate` | ✓ | ✓ | ✓ | ✓ | Blocked on Final if High/Crit open |
| `GET /api/reports/{id}/preview`, `/download` | ✓ | ✓ | ✓ | ✓ | Private storage access |
| `POST /api/reports/{id}/approve` | ✓ | ✓ | ✓ | — | Strict self-approval block (400/403) |
| `GET /api/verify/{report_id}` (Public) | ✓ | ✓ | ✓ | ✓ | Unauthenticated public portal (60/min) |
| `POST /api/verify/{report_id}/file` (Public)| ✓ | ✓ | ✓ | ✓ | In-memory SHA-256 match (30/min) |
| User CRUD (`/api/users/*`) | ✓ | — | — | — | Administrator only |
| System Settings (`/api/settings/*`) | ✓ | — | — | — | Administrator only |

---

## Quickstart Guide

### 1. Prerequisites
- **Python 3.12+** (with virtual environment capability)
- **Node.js 18+** & **npm 9+**
- *(Optional)* **Docker & Docker Compose** (for PostgreSQL 15)

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install pinned dependencies
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Seed Karnataka departments, users, settings, and demo case
python -m app.seed.seed_data

# Launch FastAPI development server on port 8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install pinned dependencies
npm install

# Run frontend dev server
npm run dev -- --port 5173
```

Open your browser at **`http://localhost:5173`**.

---

---

## Step-by-Step Demo Walkthrough

The platform includes a realistic, pre-seeded Karnataka Panchayati Raj audit environment (`make reset-demo` or `make seed`). Follow this step-by-step walkthrough to experience the entire workflow:

### 1. Login & Dashboard Overview
- Navigate to `http://localhost:5173`.
- In local development (`VITE_ENABLE_DEMO_LOGIN=true`), sign in using the quick-login demo pills or your locally seeded credentials (e.g. `auditor@stateaudit.kar.gov.in`).
- Explore the **Executive Dashboard (`/dashboard`)**:
  - Note the 12 live KPIs computed directly via SQL (zero hardcoding).
  - Open the **Priority Review Queue** drawer on the right to inspect high-exposure findings.
  - Check the Karnataka Gazetted Holidays in the Audit Calendar.

### 2. Audit Cases & Local Body Hierarchy
- Navigate to **Audit Cases (`/cases`)**.
- Notice the 5 pre-seeded cases across Karnataka districts and schemes:
  1. `CAS-2024-MYS-001` (MGNREGA - Bilikere GP, Mysuru) — *Under Review (8 findings)*
  2. `CAS-2024-BEL-002` (PMAY-G - Chikkodi TP, Belagavi) — *Under Verification (5 findings)*
  3. `CAS-2023-DHA-003` (15th FC Grants - Kundgol TP, Dharwad) — *Approved with Report*
  4. `CAS-2023-TUM-004` (Jal Jeevan Mission - Madhugiri TP, Tumakuru) — *Closed Archive*
  5. `CAS-2024-KAL-005` (Swachh Bharat Mission - Afzalpur TP, Kalaburagi) — *Clean Baseline Case (0 High/Critical findings)*
- Open `CAS-2024-MYS-001`. Notice the statutory details, local body tier hierarchy (Zilla Panchayat -> Taluk -> Gram Panchayat), 10 uploaded documents, and the case risk gauge.

### 3. Financial Verification & 16 Statutory Rules
- In the case detail header, click **Verification** or open `/verification` from the sidebar.
- Review the **Radial Risk Gauge (Score: 88, Critical Band)** with the 7-factor breakdown.
- Inspect the **Reconciliation Matrix**: 3-stage flow (Sanction -> Voucher -> Bank Debit) confirming vouchers as the true disbursement ground truth.
- Inspect the **16 Statutory Rule Cards** (R-001 through R-016), filtering by category (`Compliance`, `Financial`, `Procurement`).

### 4. Evidence Viewer & Explainability Dossier
- Navigate to **Findings (`/findings`)** and select finding `FND-MYS-001-01` (Duplicate Voucher Payment - ₹1,45,000).
- In the **Split-Pane Evidence Page (`/findings/:id`)**:
  - Left Pane: High-resolution PDF document viewer with synchronized bounding box highlight overlays and zoom controls.
  - Right Pane: 8-Tab Explainability Dossier (Extracted Values with inline overrides, Multi-Stage Reconciliation, Mathematical Calculation, Factual Reason, Threaded Notes, and Immutable Cryptographic Audit History).

### 5. Maker-Checker Dual-Custody Review
- On finding `FND-MYS-001-01` (High/Critical risk), click **Confirm Finding**.
- Supply an auditor justification note ($\ge 5$ characters) and submit.
- Notice the finding automatically transitions to **`Pending Approval`** (maker-checker governance).
- Attempting to self-approve as Auditor is blocked.
- Switch users to **Senior Auditor** (`senior.auditor@stateaudit.kar.gov.in`).
- Open `FND-MYS-001-01` and approve the finding. The status advances to **`Confirmed`** and records dual sign-off.

### 6. Statutory Report Generation & Public Verification Portal
- Open `CAS-2024-MYS-001` and click the **Reports** tab.
- Click **Generate Audit Report**:
  - The Pre-generation Blocker Gate automatically checks if any High/Critical findings remain in `Open` status.
  - Select *Interim Audit Report* or resolve remaining blockers for a *Final Statutory Report*.
  - Generate the report: ReportLab compiles the 12 statutory sections with Indian Rupee glyph (`₹`), vector QR barcode, and "DEMO DATA" watermark.
- Open **Preview Modal** to inspect the rendered PDF inline.
- Click the QR code verification link or visit:
  `http://localhost:5173/verify/RPT-2024-MYS-001`
- Test the **Zero-Knowledge Tamper Verification**:
  - Download the authentic report PDF and drag it into the file verification dropzone $\rightarrow$ Displays **VERIFIED MATCH ✓ (SHA-256 Valid)**.
  - Modify a single byte of the PDF in any text editor and re-upload $\rightarrow$ Instantly flags **TAMPER DETECTED ✗ (SHA-256 Mismatch)**.

---

## Automated Test Suites

### Backend Unit & Integration Tests (pytest)
```bash
cd backend
.venv\Scripts\Activate.ps1
pytest -v
```
*Status:* **77/77 tests passing (100%)**. Covers:
- Authentication, Argon2 hashing, token refresh, lockout, security headers.
- RBAC permission matrix for all 4 roles.
- Cryptographic hash-chaining integrity and tamper detection.
- Private document storage validation and duplicate checksum rejection.
- Indian currency parsing, Lakhs/Crores conversions, words-to-amount validation, and statutory format checks (GSTIN Luhn, PAN, IFSC).
- Document classification, tabular parser synonym mapping, and effective field value resolution.
- Complete Audit Cases and Document Ingestion REST API workflows.
- All 16 statutory verification rules (R-001 through R-016), RapidFuzz vendor matching, reconstructed records layer, and payment chain linker.
- 7-factor risk scoring engine, statutory severity floor overrides, and idempotent runner fingerprinting.
- Complete Verification REST API endpoints (`/verify`, `/summary`, `/findings`, `/matrix`, `/vendors`, `/history`, `/settings`).
- Complete Phase 4 Findings, Evidence, and Dual-Custody Review Suite (`test_phase4_findings.py`: maker-checker, self-approval prevention, state transitions, comment length, case locks, bulk operations, CSV export, notes CRUD, saved filters).
- Complete Phase 5 Cases, Dashboard, Search, and Analytics Suite (`test_phase5_cases_dashboard.py`: 7-state lifecycle, blocker gate, officer reopen & snapshots, 12 live KPIs direct SQL verification, calendar event CRUD, analytics aggregations, multi-entity search, vendor dossier).
- Complete Phase 6 Statutory Report Generator Suite (`test_phase6_reports.py`: 12-section PDF generation, Indian Rupee ₹ glyph, vector QR code, maker-checker dual custody, pre-generation blocker gate, and zero-knowledge public verification portal with 1-byte tamper detection).

### Statutory Verification & Objective Language Benchmark
```bash
cd backend
.venv\Scripts\Activate.ps1
# 1. Objective language check (zero banned accusatory terms)
pytest tests/test_banned_wording.py -s

# 2. Ground-truth anomaly detection & clean case benchmark
pytest tests/test_verification_accuracy.py -s
```
*Status:*
- Banned Subjective Words: **0 occurrences** across all 16 rules, risk engine, and test fixtures (`fraud`, `fraudulent`, `theft`, `embezzlement`, `scam`, `corrupt`, `misappropriation`).
- Master Ground-Truth Anomalies: **14/14 detected (100.0% Recall)** against `seed_ground_truth.json`.
- Clean Benchmark Case (`CAS-2024-KAL-005`): **0 High/Critical findings (100.0% Precision)**.
- Overall Anomaly F1-Score: **100.0%** (target $\ge 85\%$).

### Extraction & Classification Benchmark (ground_truth.json)
```bash
cd backend
.venv\Scripts\Activate.ps1
pytest tests/test_extraction_accuracy.py -s
```
*Status:*
- Document Classification Accuracy: **100.0%** (target $\ge 90\%$)
- Key Fields Precision: **100.0%**
- Key Fields Recall: **96.6%** (target $\ge 85\%$)

### Frontend Component Tests (Vitest)
```bash
cd frontend
npm run test
```
*Status:* **32/32 tests passing across 8 suites (100%)**. Covers:
- TanStack DataTable rendering, empty states, sorting, and filtering.
- Login form interaction and role selection.
- Confidence badge tier coloring (High green $\ge 90\%$, Medium blue $70-89\%$, Low amber $<70\%$).
- Bounding box pixel coordinate transformation math across zoom levels ($0.5\times$ to $2.5\times$) and rotation orientations ($0^\circ, 90^\circ, 180^\circ, 270^\circ$).
- Radial risk gauge SVG arc calculations, progress bars, and severity band badges.
- Reconciliation matrix 3-stage flow rendering, variance indicators, and status pill filtering.
- 16 statutory rule cards grid, category pill filtering, and count badges.
- Vendor concentration top-5 progress bars and statutory $\ge 40\%$ threshold alerts.
- Phase 4: Side-by-side reconciliation comparison table with variance highlighting.
- Phase 4: Review action dialog validation (minimum 5-character comment enforcement and maker-checker notice).
- Phase 4: Normalized bounding box overlay coordinate scaling on evidence viewer.
- Phase 5: Dashboard live KPIs, active filter propagation, and priority review queue drawer opening.
- Phase 5: Case lifecycle transition controls, blocker warning displays, and Officer reopen dialog.
- Phase 5: Analytics Recharts aggregation data structure, accessible data table toggle, and CSV export.
- Phase 5: Universal search multi-entity query parsing, result groupings, and SQLite fallback badge.
- Phase 6: Statutory report status pills, checklist blocker validation, in-app preview iframe modal, and zero-knowledge hash verification UI.

### End-to-End Playwright E2E Tests
```bash
cd frontend
npx playwright test
```
*Status:* **17/17 tests passing across all 7 test suites (100%)**. Covers:
- Complete smoke test suite across all 4 roles with role-based UI verification.
- Light/Dark theme persistence and reload stability.
- Upload/download SHA-256 binary checksum validation.
- Complete Phase 4 Findings, Evidence, and Dual-Custody workflow (Auditor -> Maker-Checker -> Senior Auditor Approval -> Self-Approval Block).
- Complete Phase 5 Case Lifecycle 7-state workflow, Blocker Gate enforcement, and Officer Reopen Snapshot.
- Live Dashboard KPIs, Scheduled Event CRUD, and Priority Review Queue.
- Analytics 8 chart visual models, accessible data table toggle, and CSV export.
- Universal search across 7 entities and basic search mode badge.
- Vendor directory and vendor dossier with PAN/GSTIN regex validation.
- Complete Phase 6 Statutory Report Generation from Case Detail, Pre-generation blocker gate, in-app preview modal, maker-checker report approval, and public zero-knowledge verification portal (`/verify/:reportId`).
- **Headless Acceptance Two-Pass Run (`final_acceptance.spec.ts`)**: Executed twice consecutively without manual cleanup:
  - **Run 1: PASSED (14.9s)**
  - **Run 2: PASSED (14.2s)**

---

## Known Limitations & ADR Fallbacks

| Feature | Production Target | Current Development Fallback | Rationale & Status |
| :--- | :--- | :--- | :--- |
| **Database** | PostgreSQL 15 | **SQLite 3 (`sqlite:///./state_audit.db`)** | Docker/Postgres was not reachable on the host machine. SQLAlchemy 2.0 dual-compatibility is preserved; PostgreSQL configuration in `docker-compose.yml` is ready for deployment. |
| **OCR Engine** | Tesseract OCR (`kan` + `eng`) | **Text-layer extraction (PyMuPDF)** | Tesseract is not installed on the host. UI explicitly displays: `OCR: Text-layer fallback mode (Tesseract not detected)`. Native PDF text layer is extracted faithfully. |
| **Search Engine** | Elasticsearch / PostgreSQL `tsvector` | **SQLite `LIKE %query%` Multi-Entity Query** | Full-text daemons unavailable locally. UI displays `Basic Search Mode (SQLite Fallback)` badge. |
| **Task Queue** | Celery + Redis | **DB-backed Job Queue + FastAPI BackgroundTasks** | Avoids external daemon dependencies for local development. |
| **QR Code Engine**| External `qrcode` pip library | **ReportLab Built-in `QrCodeWidget`** | Avoids external PyPI timeout and dependency bloat while producing crisp vector QR barcodes. |
| **Python Dependency Audit**| `pip-audit` automated CI | **Virtual Environment Packaging Scan** | Running `pip-audit` on certain Windows configurations requires active venv site-packages path resolution. All direct dependencies pinned in `requirements.txt`. |
| **Frontend Dependency Audit**| `npm audit` zero warnings | **DevDependency Tooling Notices** | 15 reported advisories belong exclusively to dev-time test runners and build tooling (`vitest`, `playwright`, `vite`, `esbuild`). Zero advisories in client runtime dependencies. |

---

## Phase Roadmap

- [x] **Phase 1: Foundation, Schema, Security, and App Shell** *(COMPLETED)*
- [x] **Phase 2: Document Ingestion, Private Storage & OCR Pipeline** *(COMPLETED)*
- [x] **Phase 3: Financial Verification & Rule Engine (Karnataka Panchayati Raj Rules)** *(COMPLETED)*
- [x] **Phase 4: Findings, Evidence, and Dual-Custody Review Workflow** *(COMPLETED)*
- [x] **Phase 5: Cases, Dashboard, Search, and Analytics** *(COMPLETED)*
- [x] **Phase 6: Statutory Report Generator & Public Integrity Verification** *(COMPLETED)*
- [x] **Step 2: Full Seed Pipeline (`make seed` & `make reset-demo`)** *(COMPLETED)*
- [x] **Step 3: Final Acceptance and Hardening** *(COMPLETED)*
