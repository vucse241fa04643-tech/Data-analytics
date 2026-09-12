import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '../ui/Card';
import { TrendingUp } from 'lucide-react';

interface LineChartCardProps {
  title: string;
  data: Record<string, any>[];
  xField: string;
  yField: string;
  unit?: string | null;
  description?: string | null;
}

export const LineChartCard: React.FC<LineChartCardProps> = ({
  title,
  data,
  xField,
  yField,
  unit,
  description,
}) => {
  const brandPrimary = '#1E3A8A';
  const brandSecondary = '#2563EB';
  const borderSubtle = '#E2E8F0';
  const textPrimary = '#0F172A';
  const textMuted = '#64748B';

  const formatUnit = (u?: string | null) => {
    if (!u) return '';
    const clean = u.trim().toLowerCase();
    if (clean === 'percentage' || clean === 'percent' || clean === '%') return '%';
    if (clean === 'count' || clean === 'integer' || clean === 'number' || clean === 'none') return '';
    if (clean === 'students') return ' students';
    if (clean === 'marks') return ' marks';
    if (clean === 'credits') return ' credits';
    if (clean === 'cgpa') return ' CGPA';
    if (clean === 'lpa') return ' LPA';
    return ` ${u}`;
  };

  const unitSuffix = formatUnit(unit);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const val = payload[0].value;
      const formattedVal =
        typeof val === 'number'
          ? Number.isInteger(val)
            ? val.toLocaleString()
            : val.toFixed(2)
          : val;

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
            {label || payload[0].payload[xField]}
          </p>
          <p style={{ margin: 0, color: brandPrimary, fontWeight: 700 }}>
            {payload[0].name || yField.replace(/_/g, ' ').toUpperCase()}: {formattedVal}
            {unitSuffix}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card
      role="region"
      aria-label={`Time series trend chart: ${title}`}
      style={{
        padding: 'var(--spacing-lg)',
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingUp size={18} color={brandSecondary} />
          <div>
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)', color: textPrimary }}>
              {title}
            </h3>
            {description && (
              <p style={{ margin: '2px 0 0 0', fontSize: 'var(--font-size-xs)', color: textMuted }}>
                {description}
              </p>
            )}
          </div>
        </div>
        <span style={{ fontSize: '11px', color: textMuted, backgroundColor: 'var(--color-bg-workspace)', padding: '2px 8px', borderRadius: '4px' }}>
          Chronological Trend
        </span>
      </div>

      <div style={{ width: '100%', height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={borderSubtle} vertical={false} />
            <XAxis
              dataKey={xField}
              stroke={textMuted}
              fontSize={11}
              tickLine={false}
              dy={8}
            />
            <YAxis
              stroke={textMuted}
              fontSize={11}
              tickLine={false}
              tickFormatter={(val) => `${val}${unitSuffix}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey={yField}
              stroke={brandPrimary}
              strokeWidth={3}
              dot={{ fill: brandSecondary, r: 4, strokeWidth: 2, stroke: '#ffffff' }}
              activeDot={{ r: 6, stroke: brandPrimary, strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
