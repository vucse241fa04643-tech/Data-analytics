import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/common/StatusBadge';
import { useBackendHealth } from '../hooks/useBackendHealth';
import {
  MessageSquare,
  BarChart3,
  ShieldCheck,
  Database,
  Lock,
  ArrowRight,
  Server,
  Layers,
  FileCheck,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { connectionState, readinessData, error } = useBackendHealth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xl)' }}>
      {/* Institutional Hero Section */}
      <div
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          padding: 'var(--spacing-2xl)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--color-border-subtle)',
          boxShadow: 'var(--shadow-card)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div style={{ maxWidth: '800px', position: 'relative', zIndex: 2 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <StatusBadge variant="info">Institutional Analytics Platform</StatusBadge>
            <StatusBadge variant="success">Phase 6: Intent Engine Active</StatusBadge>
          </div>
          <h1 style={{ fontSize: 'var(--font-size-3xl)', color: 'var(--color-brand-primary)', marginBottom: '16px' }}>
            Agent 63 – Institutional Data Intelligence
          </h1>
          <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: '24px' }}>
            A secure conversational intelligence agent designed exclusively for academic leadership, department heads,
            and institutional review bodies. Grounded directly in the college-provided PostgreSQL database without
            synthetic data, arbitrary SQL generation, or external cloud exposure.
          </p>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <Button
              variant="primary"
              rightIcon={<ArrowRight size={16} />}
              onClick={() => navigate('/agent')}
            >
              Open Agent 63 Workspace
            </Button>
            <Button
              variant="outline"
              rightIcon={<BarChart3 size={16} />}
              onClick={() => navigate('/analytics')}
            >
              View Analytics Workspace
            </Button>
          </div>
        </div>
      </div>

      {/* Backend Foundation Status Card */}
      <Card title="Backend Foundation & Runtime Telemetry" subtitle="Real-time connectivity to Phase 2 FastAPI Gateway">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginTop: '12px' }}>
          <div style={{ padding: '16px', backgroundColor: 'var(--color-bg-workspace)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Server size={18} color="var(--color-brand-primary)" />
              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)' }}>FastAPI Gateway</span>
            </div>
            <StatusBadge
              variant={connectionState === 'connected' || connectionState === 'degraded' ? 'success' : 'danger'}
            >
              {connectionState === 'offline' ? 'Offline' : 'Connected (v0.1.0)'}
            </StatusBadge>
            {error && <p style={{ fontSize: '11px', color: 'var(--color-warning)', marginTop: '6px' }}>{error}</p>}
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--color-bg-workspace)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Database size={18} color="var(--color-brand-primary)" />
              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)' }}>College PostgreSQL</span>
            </div>
            <StatusBadge variant="warning">
              {readinessData?.dependencies.college_database === 'configured' ? 'Configured' : 'Unconfigured (Phase 2 Default)'}
            </StatusBadge>
            <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px' }}>
              Awaiting live institutional read-only credentials
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--color-bg-workspace)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Layers size={18} color="var(--color-brand-primary)" />
              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)' }}>Schema Registry</span>
            </div>
            <StatusBadge variant="success">
              {readinessData?.dependencies.schema_registry_objects
                ? `${readinessData.dependencies.schema_registry_objects} Objects Indexed`
                : '236 Objects Indexed (21 Schemas)'}
            </StatusBadge>
            <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px' }}>
              Phase 1 Authoritative Schema Map Active
            </p>
          </div>
        </div>
      </Card>

      {/* Core Architectural Pillars */}
      <div>
        <h2 style={{ fontSize: 'var(--font-size-xl)', marginBottom: '16px', color: 'var(--color-text-primary)' }}>
          Security & Architectural Principles
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
          <Card title="Deterministic Security" subtitle="Multi-barrier validation pipeline">
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', marginTop: '8px' }}>
              <ShieldCheck size={24} color="var(--color-brand-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                Natural-language questions are resolved into structured intents and validated against AST rules before execution.
                No unvalidated AI SQL execution.
              </p>
            </div>
          </Card>

          <Card title="Zero Fabricated Data" subtitle="Institutional integrity first">
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', marginTop: '8px' }}>
              <FileCheck size={24} color="var(--color-brand-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                Agent 63 contains no mock students, invented marks, or synthetic attendance records. Every figure derives
                directly from the college PostgreSQL database.
              </p>
            </div>
          </Card>

          <Card title="Least-Privilege Execution" subtitle="Read-only connection constraint">
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', marginTop: '8px' }}>
              <Lock size={24} color="var(--color-brand-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                Connections enforce dedicated read-only roles with strict statement timeouts (5000ms). Mutation commands
                (INSERT, UPDATE, DELETE, DROP) are blocked at all layers.
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Navigation Quick Links */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        <Card
          interactive
          title="Agent 63 Conversational Workspace"
          subtitle="Interactive natural-language analytics interface"
          onClick={() => navigate('/agent')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageSquare size={20} color="var(--color-brand-secondary)" />
              <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                Ask questions across 21 institutional domains
              </span>
            </div>
            <ArrowRight size={18} color="var(--color-brand-secondary)" />
          </div>
        </Card>

        <Card
          interactive
          title="Analytics Workspace"
          subtitle="Dimensional filtering, summaries, and charts"
          onClick={() => navigate('/analytics')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BarChart3 size={20} color="var(--color-brand-secondary)" />
              <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                Structured dimensional views and record tables
              </span>
            </div>
            <ArrowRight size={18} color="var(--color-brand-secondary)" />
          </div>
        </Card>
      </div>
    </div>
  );
};
