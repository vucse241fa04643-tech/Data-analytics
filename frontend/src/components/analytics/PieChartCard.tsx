import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '../ui/Card';
import { PieChart as PieChartIcon } from 'lucide-react';
import { formatMetricUnit } from '../../utils/formatters';

interface PieChartCardProps {
  title: string;
  data: Record<string, any>[];
  xField: string;
  yField: string;
  unit?: string | null;
  description?: string | null;
}

const PIE_PALETTE = [
  '#1E3A8A', // Deep Navy
  '#2563EB', // Royal Blue
  '#059669', // Emerald Green
  '#D97706', // Amber
  '#7C3AED', // Violet
  '#0891B2', // Cyan
  '#DC2626', // Crimson
  '#475569', // Slate
  '#4F46E5', // Indigo
  '#0D9488', // Teal
];

export const PieChartCard: React.FC<PieChartCardProps> = ({
  title,
  data,
  xField,
  yField,
  unit,
  description,
}) => {
  const brandPrimary = '#1E3A8A';
  const borderSubtle = '#E2E8F0';
  const textPrimary = '#0F172A';
  const unitSuffix = formatMetricUnit(unit);

  // Calculate total for percentages
  const total = React.useMemo(() => {
    return data.reduce((acc, row) => {
      const val = Number(row[yField]);
      return acc + (isNaN(val) ? 0 : val);
    }, 0);
  }, [data, yField]);

  // Format data with numeric values
  const chartData = React.useMemo(() => {
    return data.map((row) => ({
      name: String(row[xField] ?? 'Unknown'),
      value: Number(row[yField]) || 0,
    }));
  }, [data, xField, yField]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0];
      const val = item.value;
      const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0';

      return (
        <div
          role="tooltip"
          style={{
            backgroundColor: '#ffffff',
            border: `1px solid ${borderSubtle}`,
            borderRadius: '6px',
            padding: '8px 12px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            fontSize: '12px',
          }}
        >
          <p style={{ margin: '0 0 4px 0', fontWeight: 600, color: textPrimary }}>
            {item.name}
          </p>
          <p style={{ margin: 0, color: item.payload?.fill || brandPrimary, fontWeight: 700 }}>
            {val.toLocaleString()} {unitSuffix} ({pct}%)
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card
      role="region"
      aria-label={`Pie chart visualization: ${title}`}
      style={{
        padding: 'var(--spacing-lg)',
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-card)',
        marginTop: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PieChartIcon size={18} color={brandPrimary} />
          <div>
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)', color: textPrimary }}>
              {title}
            </h3>
            {description && (
              <p style={{ margin: '2px 0 0 0', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
                {description}
              </p>
            )}
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              formatter={(value) => (
                <span style={{ fontSize: '12px', color: textPrimary }}>{value}</span>
              )}
            />
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="45%"
              innerRadius={45}
              outerRadius={85}
              paddingAngle={2}
            >
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={PIE_PALETTE[index % PIE_PALETTE.length]}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
