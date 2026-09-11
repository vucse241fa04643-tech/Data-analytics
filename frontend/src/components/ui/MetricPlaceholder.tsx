import React from 'react';
import { Card } from './Card';
import { StatusBadge } from '../common/StatusBadge';
import { Database } from 'lucide-react';

export interface MetricPlaceholderProps {
  label: string;
  category?: string;
  hint?: string;
}

export const MetricPlaceholder: React.FC<MetricPlaceholderProps> = ({
  label,
  category = 'Institutional KPI',
  hint = 'Awaiting read-only database connectivity',
}) => {
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {category}
        </span>
        <StatusBadge variant="neutral" showDot={false}>
          Phase 8 Query Target
        </StatusBadge>
      </div>
      <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)', marginBottom: '12px' }}>
        {label}
      </h3>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '8px', 
        padding: '12px', 
        backgroundColor: 'var(--color-bg-workspace)', 
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--color-border-subtle)',
      }}>
        <Database size={16} color="var(--color-text-muted)" />
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          {hint}
        </span>
      </div>
    </Card>
  );
};
