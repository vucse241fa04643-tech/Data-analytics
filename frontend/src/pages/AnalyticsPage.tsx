import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { apiService, ApiError } from '../services/api';
import { AgentQueryResponse } from '../types';
import { KpiCard } from '../components/analytics/KpiCard';
import { BarChartCard } from '../components/analytics/BarChartCard';
import { LineChartCard } from '../components/analytics/LineChartCard';
import { AnalyticalSummaryCard } from '../components/analytics/AnalyticalSummaryCard';
import { AnomalyInsightCard } from '../components/analytics/AnomalyInsightCard';
import { ResultTableView } from '../components/analytics/ResultTableView';
import { QueryDetailsAccordion } from '../components/analytics/QueryDetailsAccordion';
import { ExportControls } from '../components/analytics/ExportControls';
import { VerificationCard } from '../components/analytics/VerificationCard';
import {
  BarChart2,
  ShieldCheck,
  AlertCircle,
  Loader2,
  Database,
  ArrowRight,
} from 'lucide-react';

interface MetricOption {
  id: string;
  label: string;
  domain: string;
}

const APPROVED_METRICS: MetricOption[] = [
  {
    id: 'student.attendance.percentage',
    label: 'Course Attendance Rate (%)',
    domain: 'Attendance Domain',
  },
  {
    id: 'assessment.pass_rate',
    label: 'End-Semester Pass Rate (%)',
    domain: 'Assessment Domain',
  },
  {
    id: 'placement.ctc_average',
    label: 'Average Placement Package (LPA)',
    domain: 'Placement Domain',
  },
  {
    id: 'faculty.phd_percentage',
    label: 'Faculty Ph.D. Ratio (%)',
    domain: 'Faculty Domain',
  },
  {
    id: 'research.publication_count',
    label: 'Research Publications Count',
    domain: 'Research Domain',
  },
  {
    id: 'academics.student_faculty_ratio',
    label: 'Student-to-Faculty Ratio',
    domain: 'Academic Domain',
  },
];

export const AnalyticsPage: React.FC = () => {
  const [selectedMetricId, setSelectedMetricId] = useState<string>(APPROVED_METRICS[0].id);
  const [selectedDimension, setSelectedDimension] = useState<string>('department');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [queryResponse, setQueryResponse] = useState<AgentQueryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastAnalyzedMetric, setLastAnalyzedMetric] = useState<string | null>(null);

  const handleAnalyze = async (metricId?: string, dimensionOverride?: string) => {
    const targetMetricId = metricId || selectedMetricId;
    const targetDim = dimensionOverride !== undefined ? dimensionOverride : selectedDimension;
    const metricObj = APPROVED_METRICS.find((m) => m.id === targetMetricId) || APPROVED_METRICS[0];

    const token = apiService.getAuthToken();
    if (!token) {
      setErrorMessage('Institutional authentication required. Please sign in via the top-right menu.');
      return;
    }

    let prompt = `Show ${metricObj.label.toLowerCase()}`;
    if (targetDim === 'department') {
      prompt += ' by department';
    } else if (targetDim === 'year') {
      prompt += ' by academic year';
    }

    setIsLoading(true);
    setErrorMessage(null);
    setQueryResponse(null);
    setLastAnalyzedMetric(metricObj.label);

    try {
      const resp = await apiService.executeAgentQuery(prompt, false);
      setQueryResponse(resp);
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.errorCode === 'DATABASE_NOT_CONFIGURED') {
          setErrorMessage('College database is currently unavailable or unconfigured.');
        } else {
          setErrorMessage(err.message || 'Analytical query could not be executed.');
        }
      } else {
        setErrorMessage('Failed to execute analytical query against institutional database.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const result = queryResponse?.result;
  const sqlArtifact = queryResponse?.sql_artifact;
  const metadata = queryResponse?.execution_metadata || result?.metadata;
  const viz = queryResponse?.visualization;
  const explanation = queryResponse?.explanation;
  const metricDisplayName = queryResponse?.metric_display_name || viz?.title || lastAnalyzedMetric;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)', minHeight: '100%' }}>
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-primary)', margin: 0 }}>
              Institutional Analytics Workspace
            </h1>
            <StatusBadge variant="success">Phase 14 Operational</StatusBadge>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', margin: 0 }}>
            Structured dimensional analysis, KPI aggregation, verified visualizations, and institutional exports.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusBadge variant="info">
            <ShieldCheck size={14} style={{ marginRight: '4px' }} />
            <span>Read-Only PostgreSQL Verified</span>
          </StatusBadge>
        </div>
      </div>

      {/* Scope & Dimensional Filter Bar */}
      <Card
        title="Analytics Scope & Dimension Selector"
        subtitle="Select an approved institutional metric and breakdown dimension to execute AST-validated SQL"
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginTop: '12px',
          }}
        >
          {/* Metric Selector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label
              style={{
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-medium)',
                color: 'var(--color-text-secondary)',
              }}
            >
              Institutional Metric
            </label>
            <select
              value={selectedMetricId}
              onChange={(e) => setSelectedMetricId(e.target.value)}
              disabled={isLoading}
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--color-bg-workspace)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-primary)',
                cursor: 'pointer',
              }}
            >
              {APPROVED_METRICS.map((m) => (
                <option key={m.id} value={m.id}>
                  [{m.domain.replace(' Domain', '')}] {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Dimension Selector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label
              style={{
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-medium)',
                color: 'var(--color-text-secondary)',
              }}
            >
              Breakdown Dimension
            </label>
            <select
              value={selectedDimension}
              onChange={(e) => setSelectedDimension(e.target.value)}
              disabled={isLoading}
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--color-bg-workspace)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-primary)',
                cursor: 'pointer',
              }}
            >
              <option value="department">By Academic Department</option>
              <option value="none">Institutional Aggregate (Scalar)</option>
            </select>
          </div>

          {/* Action Trigger */}
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
            <Button
              variant="primary"
              onClick={() => handleAnalyze()}
              disabled={isLoading}
              style={{ width: '100%', height: '38px' }}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" style={{ marginRight: '6px' }} />
                  <span>Executing Query...</span>
                </>
              ) : (
                <>
                  <BarChart2 size={16} style={{ marginRight: '6px' }} />
                  <span>Execute Analysis</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>

      {/* Error Alert */}
      {errorMessage && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--color-danger-bg)',
            border: '1px solid var(--color-danger-border)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--color-danger)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <Card>
          <div
            style={{
              padding: 'var(--spacing-2xl) var(--spacing-lg)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
            }}
          >
            <Loader2 size={32} color="var(--color-brand-primary)" className="animate-spin" />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                Compiling AST-Validated SQL & Querying Database
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                Evaluating role authorization, enforcing read-only boundary, and generating visualization...
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Analytical Result Presentation */}
      {!isLoading && queryResponse && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
          {/* Visual Canvas (Recharts) */}
          {viz && result && (
            <div>
              {viz.chart_type === 'kpi' && result.rows.length > 0 && (
                <KpiCard
                  title={viz.title || metricDisplayName || 'Institutional Metric'}
                  value={result.rows[0][viz.y_field || result.columns[0]]}
                  unit={viz.unit}
                  description={viz.description}
                  subtitle={selectedDimension === 'department' ? 'By Department' : undefined}
                />
              )}

              {(viz.chart_type === 'bar' || viz.chart_type === 'horizontal_bar') &&
                viz.x_field &&
                viz.y_field &&
                result.rows.length > 0 && (
                  <BarChartCard
                    title={viz.title || `${metricDisplayName} Comparison`}
                    data={result.rows}
                    xField={viz.x_field}
                    yField={viz.y_field}
                    unit={viz.unit}
                    isHorizontal={viz.chart_type === 'horizontal_bar'}
                    description={viz.description}
                  />
                )}

              {viz.chart_type === 'line' &&
                viz.x_field &&
                viz.y_field &&
                result.rows.length > 0 && (
                  <LineChartCard
                    title={viz.title || `${metricDisplayName} Over Time`}
                    data={result.rows}
                    xField={viz.x_field}
                    yField={viz.y_field}
                    unit={viz.unit}
                    description={viz.description}
                  />
                )}
            </div>
          )}

          {/* Anomaly Assessment */}
          {queryResponse.anomaly && (
            <AnomalyInsightCard anomaly={queryResponse.anomaly} />
          )}

          {/* Analytical Summary Card */}
          {explanation && (
            <AnalyticalSummaryCard explanation={explanation} />
          )}

          {/* Tabular Result Representation */}
          {result && (
            <ResultTableView
              result={result}
              metadata={metadata}
              title={metricDisplayName ? `${metricDisplayName} — Verified Records` : 'Verified Records'}
            />
          )}

          {/* Phase 14 Result Export Controls */}
          {queryResponse.request_id && result && (
            <ExportControls
              requestId={queryResponse.request_id}
              rowCount={result.rows.length}
            />
          )}

          {/* Phase 14 Official Report Verification */}
          {queryResponse.request_id && (
            <VerificationCard
              requestId={queryResponse.request_id}
            />
          )}

          {/* Query Details & Audit Metadata Accordion */}
          <QueryDetailsAccordion
            metricId={queryResponse.intent?.metric_id}
            metricDisplayName={metricDisplayName}
            scope="Institutional"
            requestId={queryResponse.request_id}
            sqlArtifact={sqlArtifact}
            metadata={metadata}
          />
        </div>
      )}

      {/* Initial Empty State with Quick-Select Cards (Zero Fake Figures) */}
      {!isLoading && !queryResponse && !errorMessage && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)', margin: 0 }}>
              Curated Institutional Indicators
            </h2>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              Click an indicator to execute a live, verified analytical query
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '14px',
            }}
          >
            {APPROVED_METRICS.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  setSelectedMetricId(m.id);
                  handleAnalyze(m.id, 'department');
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  padding: '16px',
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-card)',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  gap: '12px',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-brand-secondary)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-elevated)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)';
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 'var(--font-weight-semibold)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      color: 'var(--color-brand-secondary)',
                      marginBottom: '6px',
                    }}
                  >
                    {m.domain}
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 'var(--font-weight-semibold)',
                      color: 'var(--color-text-primary)',
                      lineHeight: 1.4,
                    }}
                  >
                    {m.label}
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    paddingTop: '8px',
                    borderTop: '1px solid var(--color-border-subtle)',
                    fontSize: '11px',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Database size={12} />
                    <span>Live SQL Query</span>
                  </span>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      color: 'var(--color-brand-secondary)',
                      fontWeight: 'var(--font-weight-medium)',
                    }}
                  >
                    <span>Analyze</span>
                    <ArrowRight size={12} />
                  </span>
                </div>
              </button>
            ))}
          </div>

          <EmptyState
            icon={<BarChart2 size={32} color="var(--color-brand-secondary)" />}
            title="Institutional Analytics Engine Ready"
            description="All metrics are compiled into AST-validated SQL, executed against read-only college PostgreSQL tables, and verified against official reports with zero synthetic data."
          />
        </div>
      )}
    </div>
  );
};
export default AnalyticsPage;
