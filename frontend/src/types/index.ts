/**
 * Agent 63 – Core Frontend Type Definitions
 */

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface DependenciesStatus {
  schema_registry: string;
  college_database: string;
  schema_registry_objects?: number;
  database_host?: string | null;
}

export interface ReadinessResponse {
  status: 'ready' | 'degraded' | 'unavailable';
  service: string;
  version: string;
  dependencies: DependenciesStatus;
}

export type BackendConnectionState = 'checking' | 'connected' | 'degraded' | 'offline';

export interface NavItem {
  label: string;
  path: string;
  iconName: string;
  description?: string;
  badge?: string;
}

/**
 * Phase 6 – Structured Intent Types
 */
export type IntentValidationStatus = 'VALID' | 'CLARIFICATION_REQUIRED' | 'OUT_OF_SCOPE' | 'REJECTED';

export type IntentType =
  | 'METRIC_QUERY'
  | 'COMPARISON_QUERY'
  | 'TREND_QUERY'
  | 'RANKING_QUERY'
  | 'BREAKDOWN_QUERY'
  | 'CLARIFICATION_NEEDED'
  | 'OUT_OF_SCOPE'
  | 'UNSUPPORTED';

export interface TimeContext {
  academic_year?: string | null;
  term?: string | null;
  date_range?: Record<string, string | null> | null;
}

export interface StructuredIntent {
  intent_type: IntentType;
  metric_id?: string | null;
  primary_metric_id?: string | null;
  secondary_metric_ids?: string[];
  dimensions?: string[];
  filters?: Record<string, any>;
  time_context?: TimeContext;
  reasoning_summary?: string | null;
  clarification_questions?: string[];
}

export interface IntentRequest {
  message: string;
}

export interface IntentResponse {
  status: IntentValidationStatus;
  intent?: StructuredIntent | null;
  clarification_questions?: string[];
  message: string;
  request_id?: string | null;
}

/**
 * Phase 5 – Authentication & Principal Types
 */
export interface ScopedRole {
  role: string;
  scope_type: string;
  scope_id?: string | null;
}

export interface UserProfileResponse {
  user_id: string;
  username: string;
  email: string;
  is_active: boolean;
  roles: string[];
  scoped_roles: ScopedRole[];
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Phase 8 – Query Execution Types
 */
export type QueryResultStatus = 'SUCCESS' | 'EMPTY' | 'ERROR' | 'DATABASE_NOT_CONFIGURED';

export interface ExecutionMetadata {
  execution_time_ms: number;
  row_count: number;
  columns: string[];
  data_types?: Record<string, string>;
  executed_at: string;
  metric_id?: string | null;
  statement_timeout_ms?: number | null;
}

export interface QueryResult {
  status: QueryResultStatus;
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  metadata: ExecutionMetadata;
  error?: string | null;
}

export interface AgentQueryRequest {
  prompt: string;
  dry_run?: boolean;
  conversation_id?: string | null;
}

/**
 * Phase 9 & 10 – Visualization & Conversational Analytics Types
 */
export type ChartType = 'kpi' | 'bar' | 'horizontal_bar' | 'line' | 'table' | 'none';

export interface VisualizationDescriptor {
  recommended: boolean;
  chart_type: ChartType;
  x_field?: string | null;
  y_field?: string | null;
  title?: string | null;
  unit?: string | null;
  description?: string | null;
}

export interface AgentQueryResponse {
  intent?: Record<string, any> | null;
  sql_artifact?: Record<string, any> | null;
  result?: QueryResult | null;
  execution_metadata?: ExecutionMetadata | null;
  dry_run: boolean;
  message?: string | null;
  request_id?: string | null;
  visualization?: VisualizationDescriptor | null;
  explanation?: string | null;
  metric_display_name?: string | null;
  conversation_id?: string | null;
  is_follow_up?: boolean;
  clarification_questions?: string[];
  anomaly?: AnomalyAssessment | null;
}

/**
 * Phase 11 – Deterministic Anomaly Detection Types
 */
export type AnomalyStatus = 'NO_ANOMALY' | 'ANOMALY_DETECTED' | 'ASSESSMENT_UNAVAILABLE';
export type AnomalySeverity = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH';
export type AnomalyMethod =
  | 'NONE'
  | 'TARGET_DEVIATION'
  | 'CONFIGURED_THRESHOLD'
  | 'PERCENTAGE_DEVIATION'
  | 'HISTORICAL_Z_SCORE'
  | 'CROSS_CATEGORY_IQR'
  | 'INSUFFICIENT_DATA';

export type BaselineType =
  | 'OFFICIAL_TARGET'
  | 'HISTORICAL_BASELINE'
  | 'ANALYTICAL_HEURISTIC'
  | 'NO_BASELINE';

export interface CategoryAnomalyItem {
  category_name: string;
  observed_value: number;
  baseline_or_benchmark?: number | null;
  deviation?: number | null;
  severity: AnomalySeverity;
  explanation: string;
}

export interface AnomalyAssessment {
  status: AnomalyStatus;
  detected: boolean;
  severity: AnomalySeverity;
  method: AnomalyMethod;
  metric_id: string;
  metric_display_name?: string | null;
  observed_value?: number | null;
  baseline_value?: number | null;
  baseline_type?: BaselineType;
  deviation_value?: number | null;
  deviation_percentage?: number | null;
  confidence?: string | null;
  explanation?: string | null;
  limitations?: string | null;
  supporting_scope?: string | null;
  requires_review?: boolean;
  category_anomalies?: CategoryAnomalyItem[];
}

/**
 * Phase 12 – Role-Based Institutional Dashboard Types
 */
export type WidgetVisualizationType = 'KPI' | 'BAR_CHART' | 'LINE_CHART' | 'TABLE';
export type WidgetStatus = 'SUCCESS' | 'EMPTY' | 'UNAVAILABLE' | 'ERROR' | 'UNAUTHORIZED';

export interface DashboardCatalogItem {
  dashboard_id: string;
  title: string;
  description: string;
  role: string;
  widget_count: number;
  is_default: boolean;
}

export interface DashboardCatalogResponse {
  dashboards: DashboardCatalogItem[];
  user_roles: string[];
  active_dashboard_id?: string | null;
}

export interface DashboardWidgetResult {
  widget_id: string;
  metric_id: string;
  metric_display_name: string;
  title: string;
  visualization_type: string;
  visualization?: VisualizationDescriptor | null;
  result?: QueryResult | null;
  anomaly?: AnomalyAssessment | null;
  explanation?: string | null;
  status: WidgetStatus;
  error_message?: string | null;
  last_updated: string;
}

export interface DashboardResponse {
  dashboard_id: string;
  title: string;
  description?: string | null;
  role: string;
  scope: {
    scope_type?: string;
    scope_id?: string | null;
    display?: string;
    [key: string]: any;
  };
  generated_at: string;
  last_refreshed_at: string;
  refresh_mode: string;
  refresh_status: string;
  widgets: DashboardWidgetResult[];
}

export interface DashboardScheduleItem {
  schedule_id: string;
  dashboard_id: string;
  dashboard_title: string;
  user_id: string;
  role: string;
  interval_minutes: number;
  created_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
  is_active: boolean;
  last_status?: string | null;
}

export interface DashboardScheduleRequest {
  dashboard_id: string;
  interval_minutes: number;
}

/**
 * Phase 13 – Usage Analytics & Popular Questions Types
 */
export interface PopularQuestion {
  metric_id: string;
  label: string;
  query_type?: string | null;
  dimension_signature?: string | null;
  count: number;
  percentage?: number | null;
  last_seen: string;
}

/**
 * Phase 14 – Analytical Export & Official Report Verification Types
 */
export type ExportFormat = 'csv' | 'json';

export interface ExportRequest {
  request_id: string;
  format: ExportFormat;
}

export type VerificationStatus = 'MATCH' | 'MISMATCH' | 'NOT_COMPARABLE' | 'NOT_VERIFIED';

export interface VerificationRequest {
  request_id: string;
  document_id?: string | null;
}

export interface VerificationResult {
  status: VerificationStatus;
  metric_id: string;
  metric_display_name: string;
  analytical_value?: any;
  official_value?: any;
  unit?: string | null;
  reporting_period?: string | null;
  scope?: {
    scope_type?: string | null;
    scope_id?: string | null;
    [key: string]: any;
  } | null;
  document_reference?: {
    title?: string;
    class?: string;
    version?: string;
    approved_by?: string;
    [key: string]: any;
  } | null;
  reason: string;
  disclaimer: string;
  verified_at: string;
}

