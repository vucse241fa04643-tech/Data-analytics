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
    badge: 'Active',
    description: '26 metrics, 10 dimensions, and approved relational joins',
    isActive: true,
  },
  {
    phase: 5,
    name: 'RBAC & Scoped Access',
    badge: 'Active',
    description: 'Role-based authorization and departmental scoping boundaries',
    isActive: true,
  },
  {
    phase: 6,
    name: 'Intent Orchestration',
    badge: 'Active',
    description: 'Groq & regex intent parsing with strict validation',
    isActive: true,
  },
  {
    phase: 7,
    name: 'Safe SQL Generation',
    badge: 'Active',
    description: 'Deterministic SQLGlot AST validation & parameter binding',
    isActive: true,
  },
  {
    phase: 8,
    name: 'Read-Only PostgreSQL',
    badge: 'Active',
    description: 'Read-only transaction boundary with 1000-row & 2MB limits',
    isActive: true,
  },
  {
    phase: 9,
    name: 'Analytics & Visualization',
    badge: 'Active',
    description: 'KPI cards, Recharts visualizations, and tabular views',
    isActive: true,
    path: '/analytics',
  },
  {
    phase: 10,
    name: 'Conversation Context',
    badge: 'Active',
    description: 'Multi-turn refinement & conversational follow-ups',
    isActive: true,
    path: '/agent',
  },
  {
    phase: 11,
    name: 'Anomaly Detection',
    badge: 'Active',
    description: 'Deterministic z-score & institutional target variance',
    isActive: true,
  },
  {
    phase: 12,
    name: 'Role Dashboards',
    badge: 'Active',
    description: 'Role-based institutional dashboards with scheduled refresh',
    isActive: true,
    path: '/dashboards',
  },
  {
    phase: 13,
    name: 'Query Audit & Popular',
    badge: 'Active',
    description: 'In-memory query logging and aggregated popular questions',
    isActive: true,
  },
  {
    phase: 14,
    name: 'Export & Verification',
    badge: 'Active',
    description: 'Sanitized CSV/JSON export and official report reconciliation',
    isActive: true,
  },
];

export const PLANNED_PHASES: PlannedPhaseDefinition[] = [
  {
    phase: 15,
    name: 'Adversarial Security & Accuracy Testing',
    badge: 'Planned',
    description: 'Prompt injection, penetration testing, and accuracy reconciliation',
  },
  {
    phase: 16,
    name: 'Deployment / Production Staging',
    badge: 'Planned',
    description: 'Staging environment package, operations manual, viva demonstration',
  },
];

export const APP_PHASE = {
  CURRENT_NUMBER: 14,
  NAME: 'Analytical Export & Official Report Verification',
  STATUS_LABEL: 'Export & Verification Active',
  SYSTEM_STATUS: 'Operational • Export & Verification Active',
  SYSTEM_STATUS_UNCONFIGURED: 'Operational (DB Unconfigured)',
  EXECUTION_BOUNDARY: 'Read-Only PostgreSQL • SQL Validated • Export Ready',
  AGENT_BADGE: 'Conversational Analytics & Export',
  DASHBOARD_BADGE: 'Active',
  OVERVIEW_HERO_BADGE: 'Operational',
  SCHEMA_MAP_BADGE: 'Authoritative Schema Map Active (236 Objects)',
  FASTAPI_BADGE: 'FastAPI Gateway Connected (v0.1.0)',
  FOOTER_PHASE: 'Export & Verification',
  ACTIVE_SUBSYSTEMS,
  PLANNED_PHASES,
} as const;
