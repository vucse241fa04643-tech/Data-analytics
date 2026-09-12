import React from 'react';
import { Card } from '../ui/Card';
import { Sparkles } from 'lucide-react';

interface AnalyticalSummaryCardProps {
  explanation: string;
}

export const AnalyticalSummaryCard: React.FC<AnalyticalSummaryCardProps> = ({ explanation }) => {
  return (
    <Card
      role="region"
      aria-label="Analytical Summary"
      style={{
        padding: 'var(--spacing-md) var(--spacing-lg)',
        backgroundColor: '#F8FAFC',
        border: '1px solid #E2E8F0',
        borderLeft: '4px solid var(--color-brand-secondary)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        <Sparkles size={16} color="var(--color-brand-secondary)" />
        <h4
          style={{
            margin: 0,
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-bold)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-brand-secondary)',
          }}
        >
          Analytical Summary
        </h4>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '10px',
            color: 'var(--color-text-muted)',
            backgroundColor: '#EDF2F7',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          Deterministic Factual Synthesis
        </span>
      </div>

      <p
        style={{
          margin: 0,
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-text-primary)',
          lineHeight: 1.6,
          fontWeight: 500,
        }}
      >
        {explanation}
      </p>
    </Card>
  );
};
