export type RoleCode = "administrator" | "audit_officer" | "senior_auditor" | "auditor";

export interface Role {
  id: string;
  code: RoleCode;
  name: string;
  description?: string;
}

export interface Department {
  id: string;
  code: string;
  name: string;
  type: string;
  district?: string;
  parent_id?: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role_id: string;
  department_id?: string;
  role?: Role;
  department?: Department;
  is_active: boolean;
  failed_login_attempts: number;
  locked_until?: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface AuditCase {
  id: string;
  case_number: string;
  title: string;
  financial_year: string;
  department_id: string;
  department_name?: string;
  district?: string;
  taluk?: string;
  gram_panchayat?: string;
  scheme_name?: string;
  audit_type?: string;
  project_name?: string;
  estimated_cost?: number;
  actual_expenditure?: number;
  sanctioned_amount?: number;
  planned_start_date?: string;
  due_date?: string;
  version?: number;
  is_locked?: boolean;
  priority?: "low" | "medium" | "high" | "urgent" | string;
  lead_auditor_id?: string;
  lead_auditor_name?: string;
  status: "draft" | "documents_uploaded" | "processing" | "verification" | "review" | "approved" | "closed" | string;
  risk_level: "low" | "medium" | "high" | "critical" | string;
  remarks?: string;
  scope_notes?: string;
  document_count?: number;
  created_at: string;
  updated_at?: string;
}

export interface DocumentItem {
  id: string;
  case_id: string;
  case_number?: string;
  title: string;
  original_filename: string;
  stored_filename: string;
  file_size: number;
  mime_type: string;
  sha256_hash: string;
  document_type?: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  page_count: number;
  current_version: number;
  classification_confidence: number;
  classification_keywords?: string;
  extractor_used?: string;
  processing_error?: string;
  document_date?: string;
  uploader_id: string;
  uploader_name?: string;
  created_at: string;
  job_id?: string;
}

export interface ExtractedField {
  id: string;
  document_id: string;
  field_name: string;
  original_text?: string;
  extracted_value?: string;
  corrected_value?: string;
  effective_value?: string;
  is_overridden: boolean;
  overridden_by?: string;
  overridden_by_name?: string;
  override_comment?: string;
  confidence: number;
  source_page: number;
  bbox?: string; // JSON [x0, y0, x1, y1] normalized
  extractor: string;
  validation_status: "valid" | "invalid" | "not_checked";
  validation_message?: string;
  extracted_at: string;
}

export interface DocumentAnnotation {
  id: string;
  document_id: string;
  page: number;
  bbox?: string;
  note: string;
  finding_id?: string;
  created_by: string;
  created_by_name?: string;
  created_at: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  stored_filename: string;
  sha256_hash: string;
  file_size: number;
  document_type?: string;
  classification_confidence: number;
  change_summary?: string;
  created_by: string;
  created_by_name?: string;
  created_at: string;
}

export interface DocumentDetail extends DocumentItem {
  versions: DocumentVersion[];
  extracted_fields: ExtractedField[];
  annotations: DocumentAnnotation[];
  raw_text?: string;
}

export interface TabularTransaction {
  row_number: number;
  transaction_date: string;
  voucher_no: string;
  description: string;
  amount: number;
  debit?: number | null;
  credit?: number | null;
  balance?: number | null;
  type: string;
  raw_row?: Record<string, string>;
}

export interface TabularParseResult {
  headers: string[];
  mapping: Record<string, string>;
  confidence: number;
  total_rows: number;
  transactions: TabularTransaction[];
}

export interface AuditJob {
  id: string;
  job_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  result_json?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityLogItem {
  id: string;
  sequence_id: number;
  timestamp: string;
  actor_id?: string;
  actor_name: string;
  action: string;
  entity_type: string;
  entity_id: string;
  case_id?: string;
  prev_hash: string;
  current_hash: string;
}

export interface AuditTrailVerifyResponse {
  verified: boolean;
  total_records: number;
  broken_at_sequence?: number | null;
  last_verified_at?: string;
  message?: string;
  error?: string;
}

export interface SystemSetting {
  id: string;
  key: string;
  value_json: string;
  category: string;
  is_editable: boolean;
  updated_at: string;
}

export interface Holiday {
  id: string;
  holiday_date: string;
  name: string;
  state: string;
  description?: string;
}

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface FindingEvidence {
  record_id?: string;
  document_id?: string;
  document_number?: string;
  row?: number;
  [key: string]: any;
}

export interface Finding {
  id: string;
  case_id: string;
  rule_id: string;
  finding_number: string;
  category: string;
  title: string;
  description: string;
  reason: string;
  calculation: string;
  risk_level: RiskLevel;
  status: "Open" | "Under Review" | "Confirmed" | "Dismissed" | "Escalated" | "Auto-resolved (condition no longer detected)";
  financial_implication?: number;
  amount_at_risk?: number;
  confidence: number;
  evidence_json?: string;
  evidence?: FindingEvidence[];
  inputs_used_json?: string;
  thresholds_used_json?: string;
  data_changed_since_review: boolean;
  assigned_auditor_id?: string;
  assigned_auditor_name?: string;
  reviewed_by_id?: string;
  reviewed_by_name?: string;
  reviewed_at?: string;
  review_notes?: string;
  auto_resolved_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface RuleSummaryItem {
  rule_id: string;
  name: string;
  category: string;
  status: "pass" | "flagged" | "skipped";
  findings_count: number;
  skipped_reason?: string | null;
  default_severity: RiskLevel;
}

export interface ReconciliationMatrixItem {
  bill_id?: string | null;
  bill_number?: string | null;
  bill_amount?: number | null;
  voucher_id?: string | null;
  voucher_number?: string | null;
  voucher_amount?: number | null;
  bank_id?: string | null;
  bank_reference?: string | null;
  bank_amount?: number | null;
  status: "fully_matched" | "partially_matched" | "unmatched";
}

export interface VendorConcentrationItem {
  vendor_id: string;
  vendor_name: string;
  total_spend: number;
  payment_count: number;
  spend_share_pct: number;
  is_flagged: boolean;
}

export interface FactorBreakdown {
  missing_documents: number;
  amount_difference: number;
  duplicate_signals: number;
  vendor_concentration: number;
  unusual_amount: number;
  record_incompleteness: number;
  date_anomalies: number;
  [key: string]: number;
}

export interface CaseVerificationSummary {
  case_id: string;
  case_number: string;
  risk_score: number;
  risk_band: RiskLevel;
  factor_breakdown: FactorBreakdown;
  total_expenditure: number;
  total_findings: number;
  active_findings_count: number;
  auto_resolved_count: number;
  rules_summary: RuleSummaryItem[];
  reconciliation_matrix: ReconciliationMatrixItem[];
  vendor_concentration: VendorConcentrationItem[];
  last_run_at?: string | null;
  last_run_duration_ms?: number;
}

export interface VerificationRuleConfig {
  id: string;
  rule_code: string;
  name: string;
  description: string;
  category: string;
  is_enabled: boolean;
  default_severity: RiskLevel;
  statutory_basis?: string;
  parameters: Record<string, any>;
  default_parameters: Record<string, any>;
  last_modified_by?: string;
  last_modified_at?: string;
}

export interface RuleRunItem {
  id: string;
  case_id: string;
  rule_id: string;
  triggered_by?: string;
  triggered_by_name?: string;
  status: string;
  items_evaluated: number;
  findings_count: number;
  thresholds_snapshot: Record<string, any>;
  execution_summary?: Record<string, any>;
  duration_ms: number;
  run_at: string;
}

export interface MandatoryChecklistItem {
  id: string;
  scheme_name: string;
  document_type: string;
  is_mandatory: boolean;
  description?: string;
  created_at: string;
}

export interface PendingVendorAlias {
  id: string;
  vendor_id: string;
  vendor_name: string;
  alias_name: string;
  source: string;
  confidence_score: number;
  match_method: string;
  created_at: string;
}
