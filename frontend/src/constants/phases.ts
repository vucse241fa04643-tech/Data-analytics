/**
 * Agent 63 – Centralized Phase & Institutional Status Registry
 * Single authoritative source for application phase state and labels.
 * Prevents stale phase status indicators across navigation and headers.
 */

export const APP_PHASE = {
  CURRENT_NUMBER: 14,
  NAME: 'Phase 14: Analytical Export & Official Report Verification',
  STATUS_LABEL: 'Phase 14 • Export & Verification Active',
  SYSTEM_STATUS: 'Phase 14 Operational (Export & Verification Active)',
  SYSTEM_STATUS_UNCONFIGURED: 'Phase 14 Operational (DB Unconfigured)',
  EXECUTION_BOUNDARY: 'Read-Only PostgreSQL • SQL Validated • Export Ready',
  AGENT_BADGE: 'Phase 14 Active • Conversational Analytics & Export',
  DASHBOARD_BADGE: 'Phase 12 Active',
  OVERVIEW_HERO_BADGE: 'Phase 14 Operational',
  SCHEMA_MAP_BADGE: 'Authoritative Schema Map Active (236 Objects)',
  FASTAPI_BADGE: 'FastAPI Gateway Connected (v0.1.0)',
  FOOTER_PHASE: 'Phase 14: Export & Verification',

  // Completed system capabilities integrated into current workflow
  COMPLETED_CAPABILITIES: [
    { label: 'Role Dashboards', path: '/dashboards', phase: 'Phase 12 Active' },
    { label: 'Query Audit Log', phase: 'Phase 13 Active' },
    { label: 'Official Verification', phase: 'Phase 14 Active' },
    { label: 'RBAC Enforcement', phase: 'Phase 5 Active' },
  ],

  // Planned future phases (strictly future only)
  PLANNED_PHASES: [
    { label: 'Adversarial Security & Testing', phase: 'Phase 15' },
    { label: 'Institutional Deployment & Staging', phase: 'Phase 16' },
  ],
} as const;
