import React from 'react';
import { Card } from './Card';
import { BarChart3 } from 'lucide-react';
import { EmptyState } from '../common/EmptyState';

export interface ChartPlaceholderProps {
  title: string;
  subtitle?: string;
  height?: number;
}

export const ChartPlaceholder: React.FC<ChartPlaceholderProps> = ({
  title,
  subtitle = 'Recharts visualization canvas',
  height = 300,
}) => {
  return (
    <Card title={title} subtitle={subtitle}>
      <div style={{ minHeight: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <EmptyState
          icon={<BarChart3 size={28} />}
          title="Visualization Workspace"
          description="Visual charts (Recharts) will render automatically upon execution of authorized, verified analytical queries in Phase 9."
        />
      </div>
    </Card>
  );
};
