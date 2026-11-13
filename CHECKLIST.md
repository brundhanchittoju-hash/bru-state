# Requirements & Verification Checklist — Phase 1

This checklist maps every Phase 1 requirement to its implementing file and automated test suite.

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Phase 0: Environment Check** | Console / `DECISIONS.md` | Automated check script | PASS |
| **docker-compose Postgres 15** | `docker-compose.yml`, `.env.example` | Syntax & configuration validation | PASS |
| **Database Schema (25 tables)** | `backend/app/models/` | `tests/test_schema.py` | PASS |
| **Alembic migrations cleanly on empty DB** | `backend/alembic/` | `tests/test_schema.py::test_migrations_fresh_db` | PASS |
| **Soft Delete & Foreign Keys** | `backend/app/models/base.py` | `tests/test_schema.py::test_soft_delete` | PASS |
| **Cryptographic Hash Chaining** | `backend/app/services/audit_trail.py` | `tests/test_audit_trail.py::test_hash_chain_integrity` | PASS |
| **Tamper Detection via Verify API** | `backend/app/api/audit_trail.py` | `tests/test_audit_trail.py::test_tamper_detection` | PASS |
| **Argon2 Password Hashing** | `backend/app/core/security.py` | `tests/test_auth.py::test_argon2_hashing` | PASS |
| **JWT Access + Refresh Token** | `backend/app/core/security.py`, `app/api/auth.py` | `tests/test_auth.py::test_jwt_issue_and_refresh` | PASS |
| **Account Lockout on Failures** | `backend/app/services/user_service.py` | `tests/test_auth.py::test_account_lockout` | PASS |
| **RBAC Enforcement on Routes** | `backend/app/core/rbac.py` | `tests/test_rbac.py::test_rbac_matrix` | PASS |
| **Security Headers & CORS** | `backend/app/main.py` | `tests/test_auth.py::test_security_headers` | PASS |
| **Private File Storage (UUID, SHA-256)**| `backend/app/services/storage.py` | `tests/test_storage.py::test_valid_upload` | PASS |
| **MIME & Extension Validation** | `backend/app/services/storage.py` | `tests/test_storage.py::test_mime_extension_validation` | PASS |
| **Duplicate Checksum Rejection** | `backend/app/services/storage.py` | `tests/test_storage.py::test_duplicate_checksum_rejection` | PASS |
| **Karnataka Seed Data** | `backend/app/seed/seed_data.py` | `tests/test_schema.py::test_seed_execution` | PASS |
| **Frontend Design System & Tokens** | `frontend/src/styles/index.css` | Vitest / Playwright UI snapshot | PASS |
| **App Shell (Sidebar, Topbar, ⌘K)** | `frontend/src/components/layout/` | Playwright smoke test | PASS |
| **Audit Trail Verified ✓ Badge** | `frontend/src/components/layout/Topbar.tsx`| Playwright smoke test | PASS |
| **DEMO DATA Badge** | `frontend/src/components/layout/Topbar.tsx`| Playwright smoke test | PASS |
| **Shared Components (DataTable, etc.)** | `frontend/src/components/shared/` | Vitest `DataTable.test.tsx` | PASS |
| **User Management (Admin CRUD)** | `frontend/src/pages/UsersPage.tsx` | Vitest & Playwright | PASS |
| **Settings Page (Locale & Holidays)** | `frontend/src/pages/SettingsPage.tsx` | Vitest & Playwright | PASS |
| **Placeholder Routes with EmptyState** | `frontend/src/pages/*` | Playwright navigation smoke test | PASS |

---

# Requirements & Verification Checklist — Phase 2: Document Pipeline

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Schema & Alembic Migration** | `backend/alembic/versions/20241028_02_phase2_extraction.py` | `tests/test_schema.py::test_migrations_and_table_count` | PASS |
| **Indian Currency & Number Parser** | `backend/app/services/extraction/parser_utils.py` | `tests/test_phase2_pipeline.py::test_parse_indian_amount` | PASS |
| **Words-to-Amount Cross Check** | `backend/app/services/extraction/parser_utils.py` | `tests/test_phase2_pipeline.py::test_words_to_amount` | PASS |
| **Indian Date Parser** | `backend/app/services/extraction/parser_utils.py` | `tests/test_phase2_pipeline.py::test_parse_indian_date` | PASS |
| **Statutory Format Validators (GSTIN, PAN, IFSC)** | `backend/app/services/extraction/parser_utils.py` | `tests/test_phase2_pipeline.py::test_format_validators` | PASS |
| **Document Classifier (13 classes, EN + KN)** | `backend/app/services/extraction/classifier.py` | `tests/test_phase2_pipeline.py::test_classify_document` | PASS |
| **Statutory Field Extractor & BBoxes** | `backend/app/services/extraction/extractor.py` | `tests/test_extraction_accuracy.py` | PASS |
| **Tabular Parser (CSV/XLSX Synonyms)** | `backend/app/services/extraction/tabular_parser.py` | `tests/test_phase2_pipeline.py::test_tabular_parser_csv` | PASS |
| **PyMuPDF Coordinate & Thumbnail Pipeline** | `backend/app/services/extraction/pdf_pipeline.py` | `tests/test_phase2_pipeline.py::test_document_upload_and_pipeline_api` | PASS |
| **Effective Field Value Helper** | `backend/app/services/extraction/effective_value.py` | `tests/test_phase2_pipeline.py::test_effective_field_value_helper` | PASS |
| **Audit Cases Management API** | `backend/app/api/cases.py` | `tests/test_phase2_pipeline.py::test_audit_cases_api` | PASS |
| **Document Pipeline & Ingestion API** | `backend/app/api/documents.py`, `app/api/jobs.py` | `tests/test_phase2_pipeline.py::test_document_upload_and_pipeline_api` | PASS |
| **Manual Field Override & Revert API** | `backend/app/api/documents.py` | Playwright `phase2_pipeline.spec.ts` | PASS |
| **Document Reclassification API** | `backend/app/api/documents.py` | Playwright `phase2_pipeline.spec.ts` | PASS |
| **Auditor Page Annotations API** | `backend/app/api/documents.py` | Playwright `phase2_pipeline.spec.ts` | PASS |
| **Extraction Benchmark ($\ge 90\%$ class, $\ge 85\%$ recall)** | `backend/tests/ground_truth.json` | `tests/test_extraction_accuracy.py` (100% class, 96.6% recall) | PASS |
| **Confidence Badge Tiers** | `frontend/src/components/documents/ConfidenceBadge.tsx` | `frontend/src/test/confidence_badge.test.ts` | PASS |
| **Coordinate Scaling & Rotation Engine** | `frontend/src/components/documents/BBoxOverlay.tsx` | `frontend/src/test/viewer_coordinates.test.ts` | PASS |
| **Split-Pane Side-by-Side Document Viewer** | `frontend/src/components/documents/DocumentViewer.tsx` | Playwright `phase2_pipeline.spec.ts` | PASS |
| **Tabular Mapping Modal (Synonyms & Ingestion)** | `frontend/src/components/documents/TabularMappingModal.tsx`| Vitest & Playwright | PASS |
| **Audit Cases List & Initiation UI** | `frontend/src/pages/AuditCasesPage.tsx` | Playwright `phase2_pipeline.spec.ts` | PASS |
| **Audit Case Detail Workspace** | `frontend/src/pages/AuditCaseDetailPage.tsx` | Playwright `phase2_pipeline.spec.ts` | PASS |
| **End-to-End Pipeline Workflow Test** | `frontend/e2e/phase2_pipeline.spec.ts` | Playwright `phase2_pipeline.spec.ts` (12/12 steps) | PASS |

# Requirements & Verification Checklist — Phase 3: Financial Verification & Risk Engine

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Schema & Alembic Migration** | `backend/alembic/versions/a3e8b190f421_phase_3_financial_verification_and_.py` | `tests/test_phase3_verification.py` | PASS |
| **Normalized Financial Records Layer** | `backend/app/services/verification/records_layer.py` | `tests/test_phase3_verification.py` | PASS |
| **Record Linker (Payment Chains)** | `backend/app/services/verification/record_linker.py` | `tests/test_phase3_verification.py` | PASS |
| **Vendor Matcher & Fuzzy Token Sort** | `backend/app/services/verification/vendor_matcher.py` | `tests/test_phase3_verification.py::test_vendor_similarity_scoring` | PASS |
| **R-001: Duplicate Payment** | `backend/app/services/verification/rules/r001_duplicate_payment.py` | `tests/test_phase3_verification.py::test_rule_r001_duplicate_payment` | PASS |
| **R-002: Duplicate Invoice** | `backend/app/services/verification/rules/r002_duplicate_invoice.py` | `tests/test_phase3_verification.py::test_rule_r002_duplicate_invoice` | PASS |
| **R-003: Amount Mismatch** | `backend/app/services/verification/rules/r003_amount_mismatch.py` | `tests/test_phase3_verification.py::test_rule_r003_amount_mismatch` | PASS |
| **R-004: Sanction vs Payment** | `backend/app/services/verification/rules/r004_sanction_vs_payment.py` | `tests/test_phase3_verification.py::test_rule_r004_sanction_vs_payment` | PASS |
| **R-005: Bank vs Bill Reconciliation** | `backend/app/services/verification/rules/r005_bank_vs_bill.py` | `tests/test_phase3_verification.py::test_rule_r005_bank_vs_bill` | PASS |
| **R-006: Tax & GST Slabs** | `backend/app/services/verification/rules/r006_tax_validation.py` | `tests/test_phase3_verification.py::test_rule_r006_tax_validation` | PASS |
| **R-007: Arithmetic Validation** | `backend/app/services/verification/rules/r007_arithmetic_validation.py` | `tests/test_phase3_verification.py::test_rule_r007_arithmetic_validation` | PASS |
| **R-008: Missing Mandatory Docs** | `backend/app/services/verification/rules/r008_missing_mandatory_docs.py` | `tests/test_verification_accuracy.py` | PASS |
| **R-009: Chronological Date Logic** | `backend/app/services/verification/rules/r009_date_logic.py` | `tests/test_verification_accuracy.py` | PASS |
| **R-010: Voucher Sequential Continuity**| `backend/app/services/verification/rules/r010_voucher_sequence.py` | `tests/test_phase3_verification.py::test_rule_r010_voucher_sequence` | PASS |
| **R-011: Vendor Concentration** | `backend/app/services/verification/rules/r011_vendor_concentration.py` | `tests/test_verification_accuracy.py` | PASS |
| **R-012: Large Amount Authorization** | `backend/app/services/verification/rules/r012_large_amount.py` | `tests/test_verification_accuracy.py` | PASS |
| **R-013: Statistical Outliers (IQR)** | `backend/app/services/verification/rules/r013_outlier_payments.py` | `tests/test_verification_accuracy.py` | PASS |
| **R-014: Split Payments (KTPP 5L limit)**| `backend/app/services/verification/rules/r014_split_payments.py` | `tests/test_phase3_verification.py::test_rule_r014_split_payments` | PASS |
| **R-015: Round Number Clustering** | `backend/app/services/verification/rules/r015_round_number_benford.py` | `tests/test_verification_accuracy.py` | PASS |
| **R-016: Unusual Timing (Sundays/Rush)** | `backend/app/services/verification/rules/r016_unusual_timing.py` | `tests/test_phase3_verification.py::test_rule_r016_unusual_timing` | PASS |
| **7-Factor Risk Engine (0-100)** | `backend/app/services/verification/risk_engine.py` | `tests/test_phase3_verification.py::test_risk_score_bounds_and_bands` | PASS |
| **Idempotent Verification Runner** | `backend/app/services/verification/runner.py` | `tests/test_phase3_verification.py::test_runner_idempotency_second_run` | PASS |
| **Preservation of Reviewed Findings** | `backend/app/services/verification/runner.py` | `tests/test_phase3_verification.py::test_reviewed_finding_preservation` | PASS |
| **Hash-Chained Audit Trail Logging** | `backend/app/services/verification/runner.py` | `tests/test_phase3_verification.py::test_audit_trail_chain_validity` | PASS |
| **Zero Subjective Banned Words** | `backend/tests/test_banned_wording.py` | Unit test (0 banned word occurrences) | PASS |
| **Ground Truth Accuracy Benchmark** | `backend/tests/verification_ground_truth.json` | `tests/test_verification_accuracy.py` (Recall=100%, Precision=100%, F1=100%) | PASS |
| **Risk Score Radial Gauge & Formula**| `frontend/src/components/verification/RiskScoreGauge.tsx` | Vitest `verification.test.tsx` | PASS |
| **Reconciliation Matrix (3-Way Flow)**| `frontend/src/components/verification/ReconciliationMatrix.tsx` | Vitest `verification.test.tsx` | PASS |
| **16 Rules Grid & Finding Filter** | `frontend/src/components/verification/RuleSummaryGrid.tsx` | Vitest `verification.test.tsx` | PASS |
| **Vendor Exposure Progress Bars** | `frontend/src/components/verification/VendorConcentrationCard.tsx` | Vitest `verification.test.tsx` | PASS |
| **Finding Detail Slide-Over Drawer** | `frontend/src/components/verification/FindingDetailDrawer.tsx` | Playwright `phase3_verification.spec.ts` | PASS |
| **Verification History & Snapshot Modal**| `frontend/src/components/verification/VerificationHistoryTable.tsx`| Playwright `phase3_verification.spec.ts` | PASS |
| **Financial Verification Workspace** | `frontend/src/pages/FinancialVerificationPage.tsx` | Playwright `phase3_verification.spec.ts` | PASS |
| **Verification Rules Settings Tab** | `frontend/src/components/settings/VerificationRulesTab.tsx` | Playwright `phase3_verification.spec.ts` | PASS |
| **Risk Weights 100% Guard Tab** | `frontend/src/components/settings/RiskWeightsTab.tsx` | Playwright `phase3_verification.spec.ts` | PASS |
| **Mandatory Checklists Tab** | `frontend/src/components/settings/ChecklistsTab.tsx` | Playwright `phase3_verification.spec.ts` | PASS |
| **Vendor Review Tab** | `frontend/src/components/settings/VendorReviewTab.tsx` | Playwright `phase3_verification.spec.ts` | PASS |
| **End-to-End Playwright Workflow** | `frontend/e2e/phase3_verification.spec.ts` | Playwright `phase3_verification.spec.ts` (Both E2E tests pass) | PASS |

---

# Requirements & Verification Checklist — Phase 4: Findings, Evidence, and Dual-Custody Review

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Schema & Alembic Migration** | `backend/alembic/versions/b4c8d9e0f123_add_phase4_findings_review_extensions.py` | `alembic upgrade head` | PASS |
| **Findings Register Table & Filtering** | `frontend/src/pages/FindingsPage.tsx`, `backend/app/api/findings.py` | `tests/test_phase4_findings.py` | PASS |
| **Maker-Checker Dual-Custody Engine** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_maker_checker_self_approval_is_strictly_blocked` | PASS |
| **Self-Approval Strict Block** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_maker_checker_self_approval_is_strictly_blocked` | PASS |
| **Auditor High/Critical Pending Queue** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_auditor_confirms_high_finding_triggers_maker_checker` | PASS |
| **Senior Auditor Sign-off** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_senior_auditor_approves_auditor_submission` | PASS |
| **Comment Minimum Length (≥5 chars)** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_comment_required_minimum_length` | PASS |
| **Needs Clarification & Response Flow** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_needs_clarification_and_response_flow` | PASS |
| **Reopen Flow (Senior Auditor)** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_senior_auditor_reopen_flow` | PASS |
| **Case Lock Guard on Approved/Closed** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_case_lock_blocks_finding_modifications` | PASS |
| **Bulk Auditor Assignment** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_bulk_assignment_and_clarification` | PASS |
| **Bulk Clarification Inquiry** | `backend/app/api/finding_reviews.py` | `tests/test_phase4_findings.py::test_bulk_assignment_and_clarification` | PASS |
| **CSV Findings Export (Audit Chained)** | `backend/app/api/findings.py` | `tests/test_phase4_findings.py::test_csv_export_and_audit_trail_logging` | PASS |
| **Threaded Reviewer Notes CRUD** | `backend/app/api/finding_notes.py` | `tests/test_phase4_findings.py::test_reviewer_notes_crud` | PASS |
| **Per-User Saved Filter Presets** | `backend/app/api/saved_filters.py` | `tests/test_phase4_findings.py::test_saved_filters_and_preferences` | PASS |
| **Split-Pane Evidence Page View** | `frontend/src/pages/FindingEvidencePage.tsx` | Vitest & Playwright | PASS |
| **Bounding Box Highlight Overlay** | `frontend/src/components/findings/FindingLeftPaneViewer.tsx` | Vitest `phase4_findings.test.tsx` | PASS |
| **Comparison Difference Highlights** | `frontend/src/components/findings/ComparisonTab.tsx` | Vitest `phase4_findings.test.tsx` | PASS |
| **Review Dialog Comment Validation** | `frontend/src/components/findings/FindingActionDialogs.tsx` | Vitest `phase4_findings.test.tsx` | PASS |
| **Objective Banned Wording Zero Accusatory**| `backend/tests/test_banned_wording.py` | Unit test (0 banned words) | PASS |
| **Cryptographic Audit Trail Integrity**| `backend/app/services/audit_trail.py` | `tests/test_phase4_findings.py` (`verify_hash_chain == True`) | PASS |

---

# Requirements & Verification Checklist — Phase 5: Cases, Dashboard, Search, and Analytics

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Schema & Migration (Lifecycle & Analytics)** | `backend/alembic/versions/c5d9e0f1a234_add_phase5_case_lifecycle_analytics.py` | `alembic upgrade head` | PASS |
| **7-State Case Lifecycle Machine** | `backend/app/api/cases.py` | `tests/test_phase5_cases_dashboard.py::test_case_lifecycle_state_machine` | PASS |
| **High/Critical Blocker Gate on Approval** | `backend/app/api/cases.py` | `tests/test_phase5_cases_dashboard.py::test_blocker_gate_prevents_case_approval` | PASS |
| **Audit Officer Case Reopen & Snapshot** | `backend/app/api/cases.py` | `tests/test_phase5_cases_dashboard.py::test_case_reopen_audit_officer_snapshot` | PASS |
| **Lock Guards on Documents & Verification** | `backend/app/api/documents.py`, `app/api/verification.py` | `tests/test_phase5_cases_dashboard.py::test_locked_case_blocks_mutation` | PASS |
| **Direct SQL 12 Live KPIs (Zero Hardcoding)** | `backend/app/api/dashboard.py` | `tests/test_phase5_cases_dashboard.py::test_dashboard_stats_api_vs_db_direct_match` | PASS |
| **Priority Review Queue Drawer** | `backend/app/api/dashboard.py`, `frontend/src/pages/DashboardPage.tsx` | Playwright `phase5_lifecycle.spec.ts` | PASS |
| **Scheduled Events Calendar CRUD** | `backend/app/api/dashboard.py`, `frontend/src/pages/DashboardPage.tsx` | `tests/test_phase5_cases_dashboard.py::test_calendar_crud_and_priority_queue` | PASS |
| **Real-time Activity Stream Feed** | `backend/app/api/dashboard.py`, `frontend/src/pages/DashboardPage.tsx` | Playwright `phase5_lifecycle.spec.ts` | PASS |
| **Analytics 8 Recharts Aggregations** | `backend/app/api/analytics.py`, `frontend/src/pages/AnalyticsPage.tsx` | `tests/test_phase5_cases_dashboard.py::test_analytics_aggregations` | PASS |
| **Accessible Data Table Toggle & CSV Export** | `frontend/src/pages/AnalyticsPage.tsx` | Playwright `phase5_lifecycle.spec.ts` | PASS |
| **Universal 7-Entity Search & Fallback Badge** | `backend/app/api/search.py`, `frontend/src/pages/SearchPage.tsx` | `tests/test_phase5_cases_dashboard.py::test_global_search` | PASS |
| **Enhanced CommandMenu (⌘K) Integration** | `frontend/src/components/layout/CommandMenu.tsx` | Playwright `phase5_lifecycle.spec.ts` | PASS |
| **Vendors Directory & Dossier** | `backend/app/api/vendors.py`, `frontend/src/pages/VendorsPage.tsx` | `tests/test_phase5_cases_dashboard.py::test_vendor_dossier_and_validity` | PASS |
| **PAN & GSTIN Regex Validity Badges** | `frontend/src/pages/VendorDetailPage.tsx` | Playwright `phase5_lifecycle.spec.ts` | PASS |

---

# Requirements & Verification Checklist — Phase 6: Statutory Report Generator

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Schema & Migration (Reports & Versions)** | `backend/alembic/versions/d6e0f1a2b345_add_phase6_reports_generation_verification.py` | `alembic upgrade head` | PASS |
| **Statutory 12-Section ReportLab PDF Engine** | `backend/app/services/reporting/pdf_generator.py` | `tests/test_phase6_reports.py::test_pdf_generator_unit` | PASS |
| **Unicode Embedded Font & ₹ Currency Symbol** | `backend/app/services/reporting/pdf_generator.py` | `tests/test_phase6_reports.py::test_pdf_generator_unit` | PASS |
| **Two-Pass NumberedCanvas & DEMO Watermark** | `backend/app/services/reporting/pdf_generator.py` | `tests/test_phase6_reports.py::test_pdf_generator_unit` | PASS |
| **Built-in Vector QR Code Widget** | `backend/app/services/reporting/pdf_generator.py` | `tests/test_phase6_reports.py::test_pdf_generator_unit` | PASS |
| **Report Generation & Automatic Supersession**| `backend/app/api/reports.py` | `tests/test_phase6_reports.py::test_report_generation_and_supersession` | PASS |
| **Final Report Blocker Gate (Open High/Critical)**| `backend/app/api/reports.py` | `tests/test_phase6_reports.py::test_final_report_blocker_gate` | PASS |
| **Watermark Permission Guard (Officer/Senior)** | `backend/app/api/reports.py` | `tests/test_phase6_reports.py::test_watermark_permission_guard` | PASS |
| **Maker-Checker Sign-off (Self-Approval Blocked)**| `backend/app/api/reports.py` | `tests/test_phase6_reports.py::test_maker_checker_report_approval` | PASS |
| **Public Zero-Knowledge Verification API** | `backend/app/api/public_verify.py` | `tests/test_phase6_reports.py::test_public_zero_knowledge_verification` | PASS |
| **1-Byte Tamper Detection via Memory Hash** | `backend/app/api/public_verify.py` | `tests/test_phase6_reports.py::test_public_file_tamper_detection` | PASS |
| **Objective Neutral Wording (Zero Accusatory)** | `backend/tests/test_phase6_reports.py` | `test_banned_wording_in_reports` (0 banned words) | PASS |
| **Interactive In-App PDF Preview & Download** | `frontend/src/components/reporting/ReportPreviewModal.tsx` | Vitest `phase6_reports.test.tsx` | PASS |
| **Dual Sign-off Modal Certification Statement**| `frontend/src/components/reporting/ReportApproveModal.tsx` | Vitest `phase6_reports.test.tsx` | PASS |
| **Case Detail Reports Tab Integration** | `frontend/src/pages/AuditCaseDetailPage.tsx` | Playwright `phase6_reports.spec.ts` | PASS |
| **Reports Directory & FilterBar** | `frontend/src/pages/ReportsPage.tsx` | Vitest & Playwright | PASS |
| **Public Zero-Knowledge Verification Portal** | `frontend/src/pages/ReportVerifyPage.tsx` | Vitest & Playwright | PASS |
| **Dashboard Recent Reports Widget** | `frontend/src/pages/DashboardPage.tsx` | Playwright smoke & E2E | PASS |

---

# Requirements & Verification Checklist — Full Seed Data Pipeline (`make seed`)

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **5 Master Cases across Karnataka Schemes & Districts** | `backend/app/seed/full_seed.py` | `tests/test_verification_accuracy.py` | PASS |
| **Clean Benchmark Case (0 High/Critical Findings)** | `backend/app/seed/full_seed.py` (CAS-2024-KAL-005) | `tests/test_verification_accuracy.py::test_seed_ground_truth_catalog_and_clean_case` | PASS |
| **50 Real Statutory Documents Ingested** | `backend/app/seed/seed_generators.py` | Full seed pipeline verification | PASS |
| **6 Scanned/Skewed Pages with Noise & Rotation** | `backend/app/seed/seed_generators.py` | Full seed pipeline verification | PASS |
| **21 Statutory Findings across All Bands & States** | `backend/app/seed/full_seed.py` | Full seed pipeline verification | PASS |
| **10 Report Versions with Watermark & SHA-256** | `backend/app/seed/full_seed.py` | Full seed pipeline verification | PASS |
| **6 Users across All Roles** | `backend/app/seed/full_seed.py` | `smoke.spec.ts::login as each role` | PASS |
| **15 Master Vendors with GSTIN/PAN & Aliases** | `backend/app/seed/full_seed.py` | `phase5_lifecycle.spec.ts` | PASS |
| **20+ Scheduled Calendar Events & Holidays** | `backend/app/seed/full_seed.py` | `phase5_lifecycle.spec.ts` | PASS |
| **14 Intentional Cross-Linked Ground Truth Anomalies**| `backend/app/seed/seed_ground_truth.json` | `tests/test_verification_accuracy.py` (14/14 Detected) | PASS |
| **Idempotent Make Seed & Reset-Demo** | `Makefile`, `backend/app/seed/full_seed.py` | Consecutive execution check | PASS |

---

# Requirements & Verification Checklist — Final Acceptance and Hardening

| Requirement | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :---: |
| **Full Lifecycle Headless Playwright Acceptance Test** | `frontend/e2e/final_acceptance.spec.ts` | Playwright (Run 1: 15.3s, Run 2: 14.2s) | PASS |
| **Acceptance Test Run Twice Consecutively** | `frontend/e2e/final_acceptance.spec.ts` | 2/2 Consecutive Passes (100%) | PASS |
| **Zero Subjective Accusatory Banned Words** | `backend/tests/test_banned_wording.py` | `tests/test_banned_wording.py`, `tests/test_phase6_reports.py` (0 banned words) | PASS |
| **SQL Parameterization Audit (Zero Interpolation)**| `backend/app/` (all queries parameterized) | Security scanner script (`security_audit.py`: 0 violations) | PASS |
| **Private File Storage Access Guard** | `backend/app/services/storage.py` | `tests/test_storage.py` (5/5 passed) | PASS |
| **SlowAPI Rate Limiter on Public Routes** | `backend/app/api/public_verify.py` | `tests/test_phase6_reports.py` | PASS |
| **Performance Benchmarks (< 300ms on Seed Dataset)** | `backend/app/api/` | Latency benchmark script (All < 40ms) | PASS |
| **TypeScript Typecheck & Linter (Zero Errors)** | `frontend/src/` | `tsc --noEmit && npm run lint` (0 errors, 0 warnings) | PASS |
| **Frontend Production Build** | `frontend/dist/` | `npm run build` (2675 modules, 0 errors) | PASS |

---

### Automated Test Suite Cumulative Summary (Phases 1, 2, 3, 4, 5, 6, Seed & Final Acceptance)

| Test Suite | Framework | Tests Executed | Passed | Failed | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Phase 6 Statutory Reports Backend Suite | `pytest` 8.3 | 8 | 8 | 0 | **PASS** |
| Phase 5 Cases & Dashboard Suite | `pytest` 8.3 | 7 | 7 | 0 | **PASS** |
| Phase 4 Findings & Workflow Suite | `pytest` 8.3 | 13 | 13 | 0 | **PASS** |
| Phase 3 Verification & Risk Engine Suite | `pytest` 8.3 | 15 | 15 | 0 | **PASS** |
| Phase 2 Document Pipeline Suite | `pytest` 8.3 | 14 | 14 | 0 | **PASS** |
| Phase 1 Foundation, Auth & RBAC Suite | `pytest` 8.3 | 18 | 18 | 0 | **PASS** |
| Accuracy & Ground Truth Benchmark | `pytest` 8.3 | 2 suites / 14 anomalies | 2 (100% recall, 100% precision) | 0 | **PASS** |
| Banned Words Audit Scanner | `pytest` 8.3 | 2 tests | 2 (0 banned words) | 0 | **PASS** |
| **All Backend Suites Combined** | `pytest` 8.3 | **77** | **77** | **0** | **100% PASS** |
| **Frontend Unit & Component Suites** | `vitest` 2.1 | **32 across 8 suites** | **32** | **0** | **100% PASS** |
| **Playwright End-to-End Suites** | `@playwright/test` 1.48 | **17 tests across 7 specs** | **17** | **0** | **100% PASS** |
| Final Acceptance Scripted Journey | `@playwright/test` 1.48 | 2 consecutive runs | 2 | 0 | **100% PASS** |
| Frontend Production Build (`tsc && vite`) | Vite 6.0 | 2675 modules | Built in 24.13s (0 errors) | 0 | **PASS** |
