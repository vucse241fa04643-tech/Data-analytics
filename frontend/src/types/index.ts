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
