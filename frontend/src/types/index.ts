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
}

export interface AgentQueryResponse {
  intent?: Record<string, any> | null;
  sql_artifact?: Record<string, any> | null;
  result?: QueryResult | null;
  execution_metadata?: ExecutionMetadata | null;
  dry_run: boolean;
  message?: string | null;
  request_id?: string | null;
}

