import React from 'react';
import { Card } from '../components/ui/Card';
import { StatusBadge } from '../components/common/StatusBadge';
import { MetricPlaceholder } from '../components/ui/MetricPlaceholder';
import { ChartPlaceholder } from '../components/ui/ChartPlaceholder';
import { DataTablePlaceholder } from '../components/ui/DataTablePlaceholder';
import { Filter, ShieldAlert } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const filterDimensions = [
    { label: 'Academic Year', defaultVal: '2025-2026' },
    { label: 'Department', defaultVal: 'All Departments' },
    { label: 'Program / Degree', defaultVal: 'All Programs (B.Tech / M.Tech)' },
    { label: 'Semester', defaultVal: 'All Semesters' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xl)' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-primary)' }}>
              Institutional Analytics Workspace
            </h1>
            <StatusBadge variant="info">UI Foundation</StatusBadge>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Structured dimensional analysis, KPI aggregation, and tabular records.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusBadge variant="warning">
            <ShieldAlert size={14} style={{ marginRight: '4px' }} />
            <span>Zero Synthetic Records Allowed</span>
          </StatusBadge>
        </div>
      </div>

      {/* Dimensional Filter Bar (Inactive Foundation) */}
      <Card title="Analytics Scope & Filters" subtitle="Dimensional filtering engine (Active in Phase 8)">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '12px' }}>
          {filterDimensions.map((filter, idx) => (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', color: 'var(--color-text-muted)' }}>
                {filter.label}
              </label>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  backgroundColor: 'var(--color-bg-subtle)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-muted)',
                  cursor: 'not-allowed',
                }}
                title="Filter parameter injection connects in Phase 8"
              >
                <span>{filter.defaultVal}</span>
                <Filter size={14} color="var(--color-text-muted)" />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Summary KPI Placeholders (Zero Fabricated Figures) */}
      <div>
        <div style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ fontSize: 'var(--font-size-lg)', color: 'var(--color-text-primary)' }}>
            Institutional Key Performance Indicators
          </h2>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
            Populated strictly via read-only SQL queries
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
          <MetricPlaceholder
            label="Average Course Attendance"
            category="Attendance Domain"
            hint="Calculated from attendance.v_current_attendance"
          />
          <MetricPlaceholder
            label="End-Semester Pass Percentage"
            category="Assessment Domain"
            hint="Calculated from assessment.v_course_performance"
          />
          <MetricPlaceholder
            label="Placement Readiness Quotient"
            category="Placement Domain"
            hint="Aggregated from placement.placement_drive & skills"
          />
          <MetricPlaceholder
            label="Total Active Student Strength"
            category="Academic Domain"
            hint="Sourced from core.institution & people.student"
          />
        </div>
      </div>

      {/* Visual Chart Canvas Placeholder */}
      <ChartPlaceholder
        title="Departmental Performance Trends"
        subtitle="Dimensional multi-series visualization"
        height={320}
      />

      {/* Data Table Canvas Placeholder */}
      <DataTablePlaceholder
        title="Verified Institutional Records"
        columns={['Registration No.', 'Student Profile', 'Department', 'Course Offering', 'Attendance Status', 'Verified']}
      />
    </div>
  );
};
