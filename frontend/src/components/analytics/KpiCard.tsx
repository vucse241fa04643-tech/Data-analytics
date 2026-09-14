import React from 'react';
import { Card } from '../ui/Card';
import { StatusBadge } from '../common/StatusBadge';
import { CheckCircle2 } from 'lucide-react';

import { formatMetricUnit, isCtcMetric, formatCtcNumber } from '../../utils/formatters';

interface KpiCardProps {
  title: string;
  value: number | string;
  unit?: string | null;
  description?: string | null;
  subtitle?: string | null;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  unit,
  description,
  subtitle,
}) => {
  const isCtc = isCtcMetric(unit, title);
  let formattedValue: string;
  let formattedUnit: string;

  if (isCtc) {
    const ctc = formatCtcNumber(value);
    formattedValue = ctc.numStr;
    formattedUnit = ' lakh/year';
  } else {
    formattedUnit = formatMetricUnit(unit);
    formattedValue =
      typeof value === 'number'
        ? Number.isInteger(value)
          ? value.toLocaleString()
          : Number(value.toFixed(2)).toString()
        : String(value);
  }

  return (
    <Card
      role="region"
      aria-label={`KPI Metric: ${title}`}
      style={{
        padding: 'var(--spacing-lg)',
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-subtle)',
        borderLeft: '4px solid var(--color-brand-primary)',
        boxShadow: 'var(--shadow-card)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <span
            style={{
              fontSize: 'var(--font-size-xs)',
              fontWeight: 'var(--font-weight-semibold)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--color-text-muted)',
            }}
          >
            Result Summary • Institutional KPI
          </span>
          <h2
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 'var(--font-weight-bold)',
              color: 'var(--color-brand-primary)',
              margin: '4px 0 0 0',
            }}
          >
            {title}
          </h2>
          {subtitle && (
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: '2px 0 0 0' }}>
              {subtitle}
            </p>
          )}
        </div>

        <StatusBadge variant="success">
          <CheckCircle2 size={12} style={{ marginRight: '4px' }} />
          <span>Verified Metric</span>
        </StatusBadge>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', margin: '4px 0' }}>
        <span
          style={{
            fontSize: '2.5rem',
            fontWeight: 'var(--font-weight-bold)',
            color: 'var(--color-brand-primary)',
            lineHeight: 1,
            fontFamily: 'var(--font-family-mono, monospace)',
          }}
        >
          {formattedValue}
        </span>
        {formattedUnit && (
          <span
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-text-secondary)',
            }}
          >
            {formattedUnit}
          </span>
        )}
      </div>

      {description && (
        <div
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-muted)',
            lineHeight: 1.5,
            borderTop: '1px solid var(--color-border-subtle)',
            paddingTop: '8px',
          }}
        >
          {description}
        </div>
      )}
    </Card>
  );
};
