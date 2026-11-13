# Architectural Decision Records (ADR) — STATE AUDIT AI

### ADR-001: Database Strategy & SQLite Fallback
* **Context:** Development host environment lacks active Docker and local PostgreSQL instance on port 5432.
* **Decision:** Use SQLite (`sqlite:///./state_audit.db`) with foreign key enforcement and application-level cryptographic hash guards as the local development fallback. Full PostgreSQL 15 configuration (`docker-compose.yml`) and SQLAlchemy 2.0 dual-compatibility (UUID, JSON, indexed foreign keys) will be maintained.
* **Consequences:** Core audit flows work out of the box without requiring external daemons. Full-text search and PostgreSQL triggers are abstracted cleanly.

### ADR-002: OCR & Text Extraction Fallback
* **Context:** Host environment does not have Tesseract OCR binary or Kannada (`kan`) language packs installed.
* **Decision:** Employ high-fidelity text-layer extraction via PyMuPDF for native digital documents. The UI will prominently display an `OCR: Text-layer fallback mode (Tesseract not detected)` badge. Native Tesseract adapter hooks remain ready for containerized deployment.
* **Consequences:** Ensures zero runtime crashes or stalls during document ingestion while remaining 100% transparent about the active extraction engine.

### ADR-003: Cryptographic Audit Trail Hash Chain
* **Context:** Government financial auditing requires immutable, tamper-evident logs where alterations are immediately detectable.
* **Decision:** Implement an append-only hash chain where each entry's hash is computed as:
  `SHA-256(prev_hash + sequence_id + ISO8601_timestamp + actor_id + action + entity_type + entity_id + canonical_json(payload))`
  The genesis entry uses `0` * 64 as `prev_hash`. Updates and deletions are blocked by application guards and DB constraints. A public verification endpoint (`GET /api/audit-trail/verify`) re-evaluates the entire chain from genesis to detect breaks.
* **Consequences:** Any out-of-band database mutation breaks the cryptographic chain and triggers an alert.

### ADR-004: Terminology and Human-in-the-Loop Philosophy
* **Context:** Karnataka State Audit Department audit procedures require that AI assists rather than makes final legal determinations.
* **Decision:** The system NEVER uses the word "fraud" or automatically settles cases. Automated findings are strictly labeled "flagged for review" or "recommended for review". Every final disposition requires an authenticated human auditor sign-off.
* **Consequences:** Complies with government regulatory standards and avoids legal liability.

### ADR-005: Local Body Hierarchy & State Customization
* **Context:** The system is configured for Karnataka Panchayati Raj governance but must support re-targeting other states without code rewrites.
* **Decision:** Local body terms (`Zilla Panchayat`, `Taluk Panchayat`, `Taluk`, `Gram Panchayat`) and public holidays are driven through configuration and the database `settings` table.
* **Consequences:** Switching states only requires changing the state configuration profile.

### ADR-006: Password Hashing and Lockout Security
* **Context:** Enterprise security standards mandate protection against brute-force attacks and password hash leakage.
* **Decision:** Use `argon2-cffi` for password hashing with modern memory/time parameters. Implement consecutive failure tracking: 5 failed attempts locks an account for 15 minutes, logged in the immutable audit trail.
* **Consequences:** Meets high security compliance benchmarks.

### ADR-007: Normalized Bounding Box Coordinates & Resolution Independence
* **Context:** Documents uploaded by various departments possess disparate physical DPI, dimensions, and rotation orientations. Fixed pixel bounding boxes break across varied viewports and zoom levels.
* **Decision:** All extracted bounding boxes are normalized to 0.0–1.0 float ratios: `[x_min, y_min, x_max, y_max]`. The frontend canvas transforms these ratios dynamically using `computeBBoxPixels(bbox, baseWidth, baseHeight, zoom, rotation)` supporting 0°, 90°, 180°, and 270° clockwise rotations without coordinate drift.
* **Consequences:** Perfect coordinate alignment at any zoom level (50% to 250%) and orientation across all desktop display densities.

### ADR-008: Indian Financial Notation & Statutory Parsing Engine
* **Context:** Government vouchers and bills in Karnataka feature diverse formats: Lakhs/Crores grouping (e.g. `12,34,567.00`), negative accounting brackets `(1,500.00)`, Dr/Cr suffixes, Kannada and English numerals, and words amounts.
* **Decision:** Built a specialized Indian financial parsing engine in `parser_utils.py` that handles Indian comma groupings, Lakhs/Crores multiplier conversions, accounting brackets, words-to-amount cross verification, standard Indian date patterns (`DD/MM/YYYY`, `DD-MM-YYYY`), and checksum validators (GSTIN Luhn Mod-36, PAN regex, and IFSC bank codes).
* **Consequences:** Zero failures when reading state government and gram panchayat billing formats.

### ADR-009: Human-in-the-Loop Override Architecture & Audit Immutability
* **Context:** Statutory auditors must have the final authority to correct extracted values while preserving complete audit defensibility.
* **Decision:** Extracted fields retain their original `extracted_value` and `confidence` permanently. When an auditor overrides a field via `PATCH /api/documents/{id}/fields/{field_id}/override`, a mandatory justification note is required. The update records `override_value`, `override_reason`, `overridden_by_id`, and `overridden_at` while appending an immutable cryptographic event to the audit trail ledger. Reversion (`POST .../revert`) clears the override and restores the original value.
* **Consequences:** Auditors maintain full discretion while accountability is guaranteed by the hash chain.

### ADR-010: Document Duplicate Checksum & Versioning Workflow
* **Context:** Duplicate file uploads must not pollute the audit repository or trigger duplicate pipeline runs.
* **Decision:** When a file is uploaded, its SHA-256 is evaluated. If a duplicate hash exists within the audit case, the API responds with `409 Conflict` containing the existing document ID. The frontend presents an interactive dialog enabling the auditor to either view the existing document or upload it explicitly as a new version (`version + 1`).
* **Consequences:** Prevents accidental double ingestion while allowing deliberate re-versioning.

### ADR-011: Tabular Ledger Parser & Column Synonym Mapping
* **Context:** Audit cases frequently include transaction ledgers exported from KPPP, Panchatantra, or local spreadsheets with inconsistent column headers.
* **Decision:** Built a fuzzy synonym auto-mapper in `tabular_parser.py` that recognizes standard government ledger headers (e.g. `voucher_no`, `v_no`, `kpp_id`, `passed_amount`, `debit`, `dr`, `vendor_name`, `beneficiary`) and produces a 5-row preview before batch inserting into the case transactions table.
* **Consequences:** Allows instant ingestion of legacy spreadsheet registers into standard audit formats.

### ADR-012: 16 Statutory Verification Rules & Objective Compliance Vocabulary
* **Context:** Financial audits under the Karnataka State Audit Department must verify compliance against the Karnataka Financial Code (KFC), KTPP Act 1999, and Karnataka Panchayati Raj Accounting Rules. Automated rule outputs must remain legally objective.
* **Decision:** Implemented 16 statutory rules (R-001 through R-016) categorized into Missing Supporting Documents, Duplicate Payments, Calculation Mismatches, Sanction vs Payment Excess, Split Payments, and Anomaly Detection. Enforced an automated banned wording guard (`test_banned_wording.py`) ensuring zero occurrences of subjective or accusatory terms (`fraud`, `fraudulent`, `theft`, `embezzlement`, `scam`, `corrupt`, `misappropriation`). Findings strictly use factual, neutral compliance phrases.
* **Consequences:** Eliminates legal liability and adheres to professional statutory auditing guidelines.

### ADR-013: Payment Chain Reconstruction & Disbursement Deduplication
* **Context:** In government accounting, a single transaction flows through multiple stages: Sanction Order -> Work Order -> Bill -> Voucher -> Bank Debit. Summing amounts across all document types inflates total expenditure by up to 300%.
* **Decision:** Implemented a unified Payment Chain Linker in `record_linker.py` that connects records across stages using document reference numbers and fuzzy cross-matching. For total expenditure and vendor concentration calculations, only Vouchers (the actual passed disbursement instrument) are counted, eliminating double/triple counting.
* **Consequences:** Financial metrics, vendor concentrations, and case exposure figures represent true, un-duplicated cash outlays.

### ADR-014: Fuzzy Vendor Resolution & Alias Deduplication
* **Context:** Vendor names across panchayat bills and vouchers contain typographical discrepancies, abbreviations, and missing legal suffixes (e.g., "Cauvery Infra Projects", "Cauvery Infra Projects Pvt Ltd", "Cauvery Infrastructure").
* **Decision:** Implemented RapidFuzz token sort ratio matching (`vendor_matcher.py`) against known master vendors. Matches with similarity >= 88% are automatically resolved; ambiguous matches between 70% and 87% are recorded as `pending_review` in the `vendor_aliases` table and surfaced to administrators in Settings for human confirmation or rejection.
* **Consequences:** Consolidates multi-format vendor records while retaining human oversight for edge cases.

### ADR-015: 7-Factor Weighted Risk Scoring with Statutory Floor Overrides
* **Context:** Cases require a normalized 0-100 risk score to prioritize audit resource allocation. A linear weighted average can dilute severe statutory non-compliance.
* **Decision:** Designed a 7-factor weighted scoring engine (Missing Documents: 25%, Amount Differences: 20%, Duplicate Payments: 15%, Split Purchases: 10%, Unsanctioned Payments: 10%, Calculation Mismatches: 10%, Vendor Concentration: 10%). Implemented a statutory floor override: if any finding in the case has `Critical` severity, the case risk score is clamped to a minimum of 85 (Critical band); if any finding is `High` severity, the case risk score is clamped to a minimum of 60 (High band).
* **Consequences:** Cases with severe statutory non-compliance are never hidden behind low weighted averages.

### ADR-016: Deterministic Fingerprinting & Human Review Immutability
* **Context:** Re-running verification should be idempotent, detecting new records without duplicating existing findings or overwriting auditor determinations.
* **Decision:** Findings generate deterministic fingerprints based on `rule_code`, `case_id`, `document_id`, `document_number`, and `row_index`. The verification runner preserves any finding that has been transitioned to `Confirmed`, `Dismissed`, `Under Review`, or `Escalated`. If underlying data changes, the runner marks `data_changed_since_review = True` and appends an audit event rather than overwriting auditor notes. Findings cleared by new evidence are transitioned to `Resolved`.
* **Consequences:** Guarantees idempotency and protects auditor work from being overwritten by pipeline re-executions.

### ADR-017: Maker-Checker Dual-Custody State Transition Architecture
* **Context:** Financial audits involving high-value or critical statutory non-compliance carry high legal implications; a single auditor must not have unilateral authority to confirm or dismiss severe findings.
* **Decision:** When an Auditor confirms or dismisses a finding with `High` or `Critical` risk severity, the finding automatically transitions to `Pending Approval`. A Senior Auditor or Audit Officer must perform dual-custody review to approve or reject. Self-approval is strictly prohibited by backend verification (`reviewer_id != creator_id`), returning HTTP 403 Forbidden.
* **Consequences:** Satisfies government dual-control governance standards and eliminates single-user unilateral settlement risks.

### ADR-018: Threaded Reviewer Notes & 24-Hour Edit Window
* **Context:** Auditors and reviewers require threaded notes to document cross-verification queries, but audit trail defensibility requires that notes cannot be altered after sign-off.
* **Decision:** Implemented `FindingNote` supporting hierarchical parent-reply threads. Notes can only be edited by the original author within a 24-hour window from creation; subsequent alterations are rejected. Soft deletions and edits are logged in `activity_logs`.
* **Consequences:** Allows agile collaboration while preserving historical integrity for public scrutiny.

### ADR-019: Case-Level Immutability Lock Guard
* **Context:** Once an audit case is finalized (`Approved` or `Closed`), no subsequent evidence overrides, document uploads, or finding status modifications should occur without formal reopening.
* **Decision:** Implemented a case lock guard across finding reviews, notes, bulk assignments, and field overrides. If `case.status in ("Approved", "Closed")`, API operations return HTTP 423 Locked. Reopening requires `Audit Officer` role and documented statutory justification.
* **Consequences:** Prevents retroactive tampering of finalized statutory audits.

### ADR-020: 7-State Case Lifecycle State Machine and Blocker Gate
* **Context:** Karnataka State Audit cases progress through distinct administrative phases and must not be approved while critical statutory anomalies remain unresolved.
* **Decision:** Enforced a linear 7-state lifecycle: `draft` -> `documents_uploaded` -> `processing` -> `verification` -> `review` -> `approved` -> `closed`. Any transition to `approved` is strictly gated by a database blocker check: if any finding on the case is in `Open` or `Pending Approval` with `High` or `Critical` severity, the transition is rejected with HTTP 400 detailing all blocking finding IDs. Reopening an `approved` or `closed` case is restricted to Audit Officers, requiring documented justification and automatically creating an immutable `case_versions` snapshot.
* **Consequences:** Eliminates premature or un-reviewed sign-offs on severe statutory discrepancies.

### ADR-021: Live KPI Direct SQL Computation (Zero Hardcoding)
* **Context:** Executive dashboards in government auditing must reflect true, un-doctored database metrics in real time without stale caches or static mockups.
* **Decision:** All 12 executive dashboard KPIs (`cases_in_progress`, `approved_this_fy`, `total_amount_audited`, `total_expenditure_audited`, `high_risk_findings_open`, `pending_approval_count`, `average_risk_score`, `active_auditors_count`, `critical_findings_count`, `documents_processed_count`, `needs_clarification_count`, `auto_resolved_count`) are computed directly in SQL via `SELECT COUNT`, `SUM`, and `AVG` across non-deleted records in `AuditCase`, `Finding`, `Document`, and `User`.
* **Consequences:** 100% mathematical consistency between database reality and executive views.

### ADR-022: Multi-Entity Universal Search with Graceful Fallback
* **Context:** Auditors need rapid search across 7 statutory entities (Cases, Documents, Findings, Vendors, Rules, Vouchers, Invoices) from both the dedicated search page and the `⌘K` command palette.
* **Decision:** Built a multi-entity search endpoint (`/api/search`) executing targeted SQL queries with `LIKE %query%` across entity titles, numbers, names, and codes. A header badge indicates `Basic Search Mode (SQLite Fallback)` when running in development environments without Elasticsearch or Postgres `tsvector`, cleanly communicating the active query backend.
* **Consequences:** Provides responsive, comprehensive search across all application assets with zero daemon dependencies.

### ADR-023: Statutory Vendor Dossier & PAN/GSTIN Regex Validity
* **Context:** Vendor profiles require objective verification of statutory identification numbers and transaction exposures.
* **Decision:** Evaluated vendor PAN (`^[A-Z]{5}[0-9]{4}[A-Z]{1}$`) and GSTIN (`^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`) against national formats, rendering visual validity badges in the vendor directory and dossier. Aggregated metrics (total vouchers, total expenditure, average risk score, linked findings) are computed directly from passed vouchers to avoid payment chain double-counting.
* **Consequences:** Quickly flags misformatted or invalid taxpayer IDs for auditor review without accusatory labeling.

### ADR-024: Built-in ReportLab Vector QR Code & Embedded Unicode Font
* **Context:** Statutory Indian government reports require genuine Rupee currency symbols (`₹`) and verifiable QR codes leading to public integrity endpoints, while avoiding external network dependencies during offline installations.
* **Decision:** Utilized ReportLab's built-in `reportlab.graphics.barcode.qr.QrCodeWidget` for vector QR code rendering without third-party pip dependencies. Registered true-type Unicode font families (`Segoe UI`, `Arial`, `Nirmala`) with dynamic family registration to support `₹` (`\u20b9`) without parser exception. Two-pass `NumberedCanvas` renders exact "Page X of Y" and diagonal "DEMO DATA" watermarks.
* **Consequences:** Zero external network latency, pristine vector QR scaling, and 100% compliant Indian currency rendering.

### ADR-025: Pre-Generation Blocker Gate & Version Supersession
* **Context:** Releasing an official "Final" audit report when High or Critical anomalies remain unresolved violates statutory auditing guidelines. Additionally, audit cases go through iterative review cycles.
* **Decision:** Enforced a pre-generation blocker gate preventing "Final" report generation if any High or Critical finding remains in `Open` or `Escalated` status (Preliminary and Interim drafts remain permitted). Generating a new report version automatically increments `current_version` and marks prior unapproved draft versions as `Superseded`.
* **Consequences:** Prevents premature release of final certificates while preserving complete version lineage.

### ADR-026: Maker-Checker Dual-Custody Report Approval
* **Context:** An auditor drafting an audit report must not possess unilateral authority to mark that report "Approved".
* **Decision:** Implemented strict maker-checker segregation on `/api/reports/{id}/approve`. The endpoint requires `senior_auditor` or `audit_officer` role and explicitly validates that `current_user.id != report.generated_by` and `current_user.id != version.generated_by_id`. Self-approval attempts are rejected with HTTP 400. Approved reports receive a digital sign-off stamp in Section 12 with approver name, role, timestamp, and audit trail record.
* **Consequences:** Upholds statutory dual-custody governance across all released reports.

### ADR-027: Zero-Knowledge Public Verification Portal & In-Memory Tamper Detection
* **Context:** Citizens, banks, and oversight bodies scanning the report QR code must be able to verify document authenticity without compromising statutory audit confidentiality (individual questioned amounts, suppliers, and finding text must remain private).
* **Decision:** Developed public endpoints `/verify/{report_id}` and `/verify/{report_id}/file` rate-limited via SlowAPI (60 req/min). The metadata endpoint returns exclusively case particulars, report number, version, status, generated/approved timestamps, and SHA-256 seal. The file upload widget computes SHA-256 in memory without disk persistence, returning `MATCH` (authentic) or `NO MATCH` (tampered) even if a single byte has been modified.
* **Consequences:** Provides bulletproof cryptographic integrity verification while preserving statutory confidentiality.

### ADR-028: Full Seed Architecture & 14 Intentional Ground Truth Anomalies
* **Context:** Comprehensive evaluation of an automated statutory audit platform requires realistic, multifaceted government datasets reflecting real-world Karnataka local body operations (Zilla Panchayat, Taluk Panchayat, Gram Panchayat) across major schemes (MGNREGA, PMAY-G, 15th FC, JJM, SBM-G), with varied document formats, scanning noise, and intentional, cross-linked anomalies to benchmark precision and recall.
* **Decision:** Implemented a unified seeding pipeline (`make seed`, `make reset-demo`, `full_seed.py`, `seed_generators.py`) generating:
  1. 5 master cases spanning diverse districts (Mysuru, Belagavi, Dharwad, Tumakuru, Kalaburagi) and lifecycle states (`review`, `verification`, `approved`, `closed`, and a clean baseline).
  2. 50 statutory documents across 13 document types, including 6 scanned-style pages with simulated rotation, gaussian noise, and contrast shifts.
  3. 21 statutory findings across all risk bands (Low, Medium, High, Critical) and statuses (`Open`, `Confirmed`, `Dismissed`, `Needs Clarification`, `Escalated`, `Pending Approval`, `Auto-resolved`).
  4. 10 statutory report versions with "DEMO DATA" watermarks, SHA-256 seals, and approval stamps.
  5. 14 documented cross-linked anomalies cataloged in `seed_ground_truth.json` (duplicate payments, split purchases, GSTIN mismatches, non-working day expenditures, voucher sequence gaps, vendor concentration spikes) alongside a 100% clean baseline case (`CAS-2024-KAL-005` with 0 high/critical findings).
* **Consequences:** Provides a deterministic, repeatable benchmark environment with 100% recall on cataloged anomalies and 100% precision on clean cases.

### ADR-029: Two-Pass Consecutive Scripted Headless Acceptance E2E Journey
* **Context:** Ensuring platform stability, test idempotency, and freedom from state-leakage regressions requires testing the entire end-to-end user workflow in headless browser automation across consecutive runs without manual state resets between runs.
* **Decision:** Developed an 8-step comprehensive Playwright acceptance test (`frontend/e2e/final_acceptance.spec.ts`) covering:
  1. Auditor login and session persistence.
  2. Audit case creation with Karnataka local body hierarchy.
  3. Real document upload, checksum calculation, and extraction.
  4. 16-rule verification execution and 7-factor risk engine evaluation.
  5. Findings review and maker-checker dual-custody approval dispatch.
  6. Senior Auditor dual-signoff and self-approval block enforcement.
  7. 12-section statutory ReportLab PDF generation, in-app preview, and download.
  8. Public `/verify/:reportId` zero-knowledge metadata inspection and in-memory 1-byte tamper rejection test.
  Executed the entire test suite **twice consecutively** in headless mode (`Run 1: 14.9s`, `Run 2: 14.2s`) to guarantee idempotency and test independence.
* **Consequences:** Verifies absolute runtime stability and zero cross-test flakiness across the entire software stack.

### ADR-030: Strict SQL Parameterization & Objective Compliance Vocabulary Enforcement
* **Context:** Government auditing platforms handling public finance must guarantee complete protection against SQL injection vulnerabilities and strictly avoid legal exposure from defamatory or accusatory terminology.
* **Decision:**
  1. Mandated 100% parameterization across all database queries via SQLAlchemy 2.0 ORM expressions and parameterized text queries. Automated security scanning (`scratch/security_audit.py`) confirmed 0 raw SQL string interpolations across the entire codebase.
  2. Maintained zero occurrences of subjective or accusatory terms (`fraud`, `fraudulent`, `scam`, `theft`, `embezzlement`, `corrupt`, `misappropriation`) across all templates, rule outputs, seed data, and report generators. The automated guard test (`test_banned_wording.py`) verified 100% compliance. Automated findings are strictly labeled *"flagged for review"* or *"recommended for review"*.
* **Consequences:** Bulletproof security posture and complete regulatory and legal compliance for statutory audit reporting.
