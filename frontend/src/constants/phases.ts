/**
 * Agent 63 – Centralized Phase & Institutional Status Registry
 * Single authoritative source for application phase state, labels,
 * active subsystem definitions, and planned phase definitions.
 */

export interface SubsystemDefinition {
  phase: number;
  name: string;
  badge: string;
  description: string;
  isActive: boolean;
  path?: string;
}

export interface PlannedPhaseDefinition {
  phase: number;
  name: string;
  badge: string;
  description: string;
}

export const ACTIVE_SUBSYSTEMS: SubsystemDefinition[] = [
  {
    phase: 4,
    name: 'Semantic Metrics',
    badge: 'Phase 4 Active',
    description: '26 metrics, 10 dimensions, and approved relational joins',
    isActive: true,
  },
  {
    phase: 5,
    name: 'RBAC & Scoped Access',
    badge: 'Phase 5 Active',
    description: 'Role-based authorization and departmental scoping boundaries',
    isActive: true,
  },
  {
    phase: 6,
    name: 'Intent Orchestration',
    badge: 'Phase 6 Active',
    description: 'Groq & regex intent parsing with strict validation',
    isActive: true,
  },
  {
    phase: 7,
    name: 'Safe SQL Generation',
    badge: 'Phase 7 Active',
    description: 'Deterministic SQLGlot AST validation & parameter binding',
    isActive: true,
  },
  {
    phase: 8,
    name: 'Read-Only PostgreSQL',
    badge: 'Phase 8 Active',
    description: 'Read-only transaction boundary with 1000-row & 2MB limits',
    isActive: true,
  },
  {
    phase: 9,
    name: 'Analytics & Visualization',
    badge: 'Phase 9 Active',
    description: 'KPI cards, Recharts visualizations, and tabular views',
    isActive: true,
    path: '/analytics',
  },
  {
    phase: 10,
    name: 'Conversation Context',
    badge: 'Phase 10 Active',
    description: 'Multi-turn refinement & conversational follow-ups',
    isActive: true,
    path: '/agent',
  },
  {
    phase: 11,
    name: 'Anomaly Detection',
    badge: 'Phase 11 Active',
    description: 'Deterministic z-score & institutional target variance',
    isActive: true,
  },
  {
    phase: 12,
    name: 'Role Dashboards',
    badge: 'Phase 12 Active',
    description: 'Role-based institutional dashboards with scheduled refresh',
    isActive: true,
    path: '/dashboards',
  },
  {
    phase: 13,
    name: 'Query Audit & Popular',
    badge: 'Phase 13 Active',
    description: 'In-memory query logging and aggregated popular questions',
    isActive: true,
  },
  {
    phase: 14,
    name: 'Export & Verification',
    badge: 'Phase 14 Active',
    description: 'Sanitized CSV/JSON export and official report reconciliation',
    isActive: true,
  },
];

export const PLANNED_PHASES: PlannedPhaseDefinition[] = [
  {
    phase: 15,
    name: 'Adversarial Security & Accuracy Testing',
    badge: 'Phase 15',
    description: 'Prompt injection, penetration testing, and accuracy reconciliation',
  },
  {
    phase: 16,
    name: 'Deployment / Production Staging',
    badge: 'Phase 16',
    description: 'Staging environment package, operations manual, viva demonstration',
  },
];

export const APP_PHASE = {
  CURRENT_NUMBER: 14,
  NAME: 'Phase 14: Analytical Export & Official Report Verification',
  STATUS_LABEL: 'Phase 14 • Export & Verification Active',
  SYSTEM_STATUS: 'Phase 14 Operational • Export & Verification Active',
  SYSTEM_STATUS_UNCONFIGURED: 'Phase 14 Operational (DB Unconfigured)',
  EXECUTION_BOUNDARY: 'Read-Only PostgreSQL • SQL Validated • Export Ready',
  AGENT_BADGE: 'Phase 14 Active • Conversational Analytics & Export',
  DASHBOARD_BADGE: 'Phase 12 Active',
  OVERVIEW_HERO_BADGE: 'Phase 14 Operational',
  SCHEMA_MAP_BADGE: 'Authoritative Schema Map Active (236 Objects)',
  FASTAPI_BADGE: 'FastAPI Gateway Connected (v0.1.0)',
  FOOTER_PHASE: 'Phase 14: Export & Verification',
  ACTIVE_SUBSYSTEMS,
  PLANNED_PHASES,
} as const;
