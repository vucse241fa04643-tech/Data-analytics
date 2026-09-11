import React from 'react';
import { Card } from './Card';
import { Table, ShieldCheck } from 'lucide-react';
import { EmptyState } from '../common/EmptyState';

export interface DataTablePlaceholderProps {
  title: string;
  columns?: string[];
}

export const DataTablePlaceholder: React.FC<DataTablePlaceholderProps> = ({
  title,
  columns = ['Record ID', 'Academic Department', 'Metric Value', 'Status', 'Audit Timestamp'],
}) => {
  return (
    <Card title={title} subtitle="Tabular institutional record view">
      <div style={{ overflowX: 'auto', marginBottom: '16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--font-size-sm)' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--color-border-subtle)', backgroundColor: 'var(--color-bg-workspace)' }}>
              {columns.map((col, idx) => (
                <th key={idx} style={{ padding: '12px 16px', color: 'var(--color-text-secondary)', fontWeight: 'var(--font-weight-semibold)' }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
        </table>
      </div>
      <EmptyState
        icon={<Table size={28} />}
        title="Authorized Records Only"
        description="Tabular details will populate strictly from college PostgreSQL read-only query results once institutional credentials are provided."
        action={
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--color-brand-primary)' }}>
            <ShieldCheck size={16} />
            <span>Zero synthetic records generated</span>
          </div>
        }
      />
    </Card>
  );
};
