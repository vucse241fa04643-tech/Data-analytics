import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card } from '../ui/Card';
import { BarChart3 } from 'lucide-react';

interface BarChartCardProps {
  title: string;
  data: Record<string, any>[];
  xField: string;
  yField: string;
  unit?: string | null;
  isHorizontal?: boolean;
  description?: string | null;
}

export const BarChartCard: React.FC<BarChartCardProps> = ({
  title,
  data,
  xField,
  yField,
  unit,
  isHorizontal = false,
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

  // Custom accessible tooltip
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

  const chartHeight = isHorizontal ? Math.max(280, data.length * 40) : 320;

  return (
    <Card
      role="region"
      aria-label={`Bar chart visualization: ${title}`}
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
          <BarChart3 size={18} color={brandPrimary} />
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
          {isHorizontal ? 'Horizontal Bar' : 'Column Bar'}
        </span>
      </div>

      <div style={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          {isHorizontal ? (
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 40, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={borderSubtle} horizontal={false} />
              <XAxis
                type="number"
                stroke={textMuted}
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) => `${val}${unitSuffix}`}
              />
              <YAxis
                type="category"
                dataKey={xField}
                stroke={textMuted}
                fontSize={11}
                tickLine={false}
                width={80}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yField} fill={brandPrimary} radius={[0, 4, 4, 0]}>
                {data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={index % 2 === 0 ? brandPrimary : brandSecondary}
                  />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <BarChart
              data={data}
              margin={{ top: 10, right: 20, left: 10, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={borderSubtle} vertical={false} />
              <XAxis
                dataKey={xField}
                stroke={textMuted}
                fontSize={11}
                tickLine={false}
                interval={0}
                tick={(props: any) => {
                  const { x, y, payload } = props;
                  const text = String(payload.value);
                  const displayText = text.length > 14 ? `${text.slice(0, 12)}…` : text;
                  return (
                    <g transform={`translate(${x},${y})`}>
                      <text
                        x={0}
                        y={0}
                        dy={12}
                        textAnchor="middle"
                        fill={textMuted}
                        fontSize={11}
                      >
                        {displayText}
                      </text>
                    </g>
                  );
                }}
              />
              <YAxis
                stroke={textMuted}
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) => `${val}${unitSuffix}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yField} fill={brandPrimary} radius={[4, 4, 0, 0]}>
                {data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={index % 2 === 0 ? brandPrimary : brandSecondary}
                  />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
