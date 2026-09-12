import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { StatusBadge } from '../common/StatusBadge';
import {
  ChevronDown,
  ChevronUp,
  FileCheck2,
  Terminal,
} from 'lucide-react';
import { ExecutionMetadata } from '../../types';

interface QueryDetailsAccordionProps {
  metricId?: string | null;
  metricDisplayName?: string | null;
  scope?: string | null;
  requestId?: string | null;
  sqlArtifact?: Record<string, any> | null;
  metadata?: ExecutionMetadata | null;
}

export const QueryDetailsAccordion: React.FC<QueryDetailsAccordionProps> = ({
  metricId,
  metricDisplayName,
  scope,
  requestId,
  sqlArtifact,
  metadata,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card
      role="region"
      aria-label="Query details and audit metadata"
      style={{
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--color-bg-surface)',
        overflow: 'hidden',
      }}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        style={{
          width: '100%',
          padding: '12px 16px',
          backgroundColor: 'var(--color-bg-workspace)',
          border: 'none',
          borderBottom: isOpen ? '1px solid var(--color-border-subtle)' : 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background-color 0.15s ease',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileCheck2 size={16} color="var(--color-brand-primary)" />
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-brand-primary)' }}>
            Query Details &amp; Institutional Governance Audit
          </span>
          <div style={{ display: 'flex', gap: '6px', marginLeft: '8px' }}>
            <StatusBadge variant="neutral">Read-Only</StatusBadge>
            <StatusBadge variant="success">AST Validated</StatusBadge>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-text-muted)', fontSize: '11px' }}>
          <span>{isOpen ? 'Hide Details' : 'Show Details'}</span>
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {isOpen && (
        <div style={{ padding: 'var(--spacing-md) var(--spacing-lg)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Metadata Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '12px',
              backgroundColor: 'var(--color-bg-workspace)',
              padding: '12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-xs)',
            }}
          >
            <div>
              <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '10px', textTransform: 'uppercase' }}>
                Metric Name
              </span>
              <strong style={{ color: 'var(--color-text-primary)' }}>
                {metricDisplayName || metricId || 'Institutional Metric'}
              </strong>
            </div>

            <div>
              <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '10px', textTransform: 'uppercase' }}>
                Internal Semantic ID
              </span>
              <code style={{ color: 'var(--color-brand-primary)', fontFamily: 'monospace' }}>
                {metricId || 'N/A'}
              </code>
            </div>

            <div>
              <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '10px', textTransform: 'uppercase' }}>
                Governance Scope
              </span>
              <span style={{ color: 'var(--color-text-primary)' }}>
                {scope || 'Role-Scoped'}
              </span>
            </div>

            <div>
              <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '10px', textTransform: 'uppercase' }}>
                Audit Trace ID
              </span>
              <code style={{ color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>
                {requestId ? requestId.slice(0, 12) : 'N/A'}
              </code>
            </div>

            {metadata && (
              <>
                <div>
                  <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '10px', textTransform: 'uppercase' }}>
                    Execution Time
                  </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>
                    {metadata.execution_time_ms.toFixed(1)} ms
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '10px', textTransform: 'uppercase' }}>
                    Validated Rows
                  </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>
                    {metadata.row_count}
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Compiled SQL Artifact */}
          {sqlArtifact && (
            <div style={{ border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#1e293b',
                  color: '#94a3b8',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Terminal size={14} />
                <span>Deterministic Compiled SQL (Parameterized AST)</span>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#0f172a', color: '#f8fafc', overflowX: 'auto' }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '12px', lineHeight: 1.5 }}>
                  {sqlArtifact.sql}
                </pre>
              </div>

              {sqlArtifact.parameters && Object.keys(sqlArtifact.parameters).length > 0 && (
                <div
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#1e293b',
                    borderTop: '1px solid #334155',
                    fontSize: '11px',
                    display: 'flex',
                    gap: '12px',
                    flexWrap: 'wrap',
                    color: '#cbd5e1',
                  }}
                >
                  <span style={{ fontWeight: 'bold' }}>Bound Parameters:</span>
                  {Object.entries(sqlArtifact.parameters).map(([k, v]) => (
                    <span key={k} style={{ fontFamily: 'monospace', color: '#60a5fa' }}>
                      :{k} = {JSON.stringify(v)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
