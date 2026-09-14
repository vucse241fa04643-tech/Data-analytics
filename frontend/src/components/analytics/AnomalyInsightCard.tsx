import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { AnomalyAssessment, AnomalySeverity } from '../../types';
import { AlertTriangle, CheckCircle, Info, ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { formatScopeDisplay } from '../../utils/formatters';

interface AnomalyInsightCardProps {
  anomaly?: AnomalyAssessment | null;
}

export const AnomalyInsightCard: React.FC<AnomalyInsightCardProps> = ({ anomaly }) => {
  const { user } = useAuth();
  const [showDetails, setShowDetails] = useState(false);

  if (!anomaly) {
    return null;
  }

  // Format method name for human readability
  const formatMethod = (method: string) => {
    switch (method) {
      case 'TARGET_DEVIATION':
        return 'Institutional Target Variance';
      case 'CONFIGURED_THRESHOLD':
        return 'Configured Analytical Benchmark';
      case 'HISTORICAL_Z_SCORE':
        return 'Historical Statistical Deviation (Z-Score)';
      case 'CROSS_CATEGORY_IQR':
        return 'Cross-Sectional Interquartile Distribution (IQR)';
      case 'PERCENTAGE_DEVIATION':
        return 'Percentage Baseline Deviation';
      default:
        return method;
    }
  };

  // Format baseline provenance
  const formatBaselineType = (type?: string) => {
    switch (type) {
      case 'OFFICIAL_TARGET':
        return 'Baseline: Official KPI Target';
      case 'HISTORICAL_BASELINE':
        return 'Baseline: Historical Observations';
      case 'ANALYTICAL_HEURISTIC':
        return 'Detection Rule: Analytical Heuristic';
      case 'NO_BASELINE':
      default:
        return null;
    }
  };

  // Severity styling
  const getSeverityBadge = (severity: AnomalySeverity) => {
    switch (severity) {
      case 'HIGH':
        return {
          bg: '#FEF2F2',
          border: '#FCA5A5',
          text: '#991B1B',
          label: 'High Deviation',
        };
      case 'MEDIUM':
        return {
          bg: '#FFFBEB',
          border: '#FCD34D',
          text: '#92400E',
          label: 'Moderate Deviation',
        };
      case 'LOW':
      default:
        return {
          bg: '#EFF6FF',
          border: '#BFDBFE',
          text: '#1E40AF',
          label: 'Minor Deviation',
        };
    }
  };

  // 1. NO ANOMALY STATE
  if (anomaly.status === 'NO_ANOMALY') {
    const provenanceLabel = formatBaselineType(anomaly.baseline_type);
    return (
      <Card
        role="region"
        aria-label="Anomaly Assessment: No Anomaly Detected"
        style={{
          padding: 'var(--spacing-sm) var(--spacing-md)',
          backgroundColor: '#F8FAFC',
          border: '1px solid #E2E8F0',
          borderLeft: '4px solid #10B981',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <CheckCircle size={16} color="#10B981" />
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: '#065F46' }}>
            No statistical anomaly detected
          </span>
          {provenanceLabel && (
            <span
              style={{
                fontSize: '11px',
                color: '#047857',
                backgroundColor: '#ECFDF5',
                padding: '2px 6px',
                borderRadius: '4px',
                border: '1px solid #A7F3D0',
              }}
            >
              {provenanceLabel}
            </span>
          )}
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginLeft: 'auto' }}>
            Within expected statistical distributions
          </span>
        </div>
      </Card>
    );
  }

  // 2. ASSESSMENT UNAVAILABLE STATE
  if (anomaly.status === 'ASSESSMENT_UNAVAILABLE') {
    return (
      <Card
        role="region"
        aria-label="Anomaly Assessment Unavailable"
        style={{
          padding: 'var(--spacing-sm) var(--spacing-md)',
          backgroundColor: '#F8FAFC',
          border: '1px solid #E2E8F0',
          borderLeft: '4px solid #94A3B8',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Info size={16} color="#64748B" />
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: '#475569' }}>
            Anomaly assessment unavailable
          </span>
          {anomaly.limitations && (
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginLeft: '8px' }}>
              — {anomaly.limitations}
            </span>
          )}
        </div>
      </Card>
    );
  }

  // 3. ANOMALY DETECTED STATE
  const badge = getSeverityBadge(anomaly.severity);
  const baselineLabel = formatBaselineType(anomaly.baseline_type);

  return (
    <Card
      role="region"
      aria-label="Potential Anomaly Detected"
      style={{
        padding: 'var(--spacing-md) var(--spacing-lg)',
        backgroundColor: '#FFFDF9',
        border: '1px solid #FED7AA',
        borderLeft: '4px solid #D97706',
        borderRadius: 'var(--radius-md)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
        <AlertTriangle size={18} color="#D97706" />
        <h4
          style={{
            margin: 0,
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-bold)',
            color: '#92400E',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          Potential Anomaly Detected
        </h4>

        {/* Severity Badge */}
        <span
          style={{
            backgroundColor: badge.bg,
            border: `1px solid ${badge.border}`,
            color: badge.text,
            fontSize: '11px',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '4px',
          }}
        >
          {badge.label}
        </span>

        {/* Baseline Provenance Badge */}
        {baselineLabel && (
          <span
            style={{
              backgroundColor: anomaly.baseline_type === 'OFFICIAL_TARGET' ? '#ECFDF5' : '#F1F5F9',
              border: anomaly.baseline_type === 'OFFICIAL_TARGET' ? '1px solid #A7F3D0' : '1px solid #E2E8F0',
              color: anomaly.baseline_type === 'OFFICIAL_TARGET' ? '#065F46' : '#475569',
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '4px',
            }}
          >
            {baselineLabel}
          </span>
        )}

        {/* Scope Tag */}
        {anomaly.supporting_scope && (
          <span
            style={{
              backgroundColor: '#F8FAFC',
              border: '1px solid #E2E8F0',
              color: '#475569',
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '4px',
            }}
          >
            Scope: {formatScopeDisplay(anomaly.supporting_scope, user?.roles)}
          </span>
        )}

        {/* Method Badge */}
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '11px',
            color: '#78716C',
            backgroundColor: '#F5F5F4',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {formatMethod(anomaly.method)}
        </span>
      </div>

      {/* Metrics comparison banner if observed and baseline are present */}
      {(anomaly.observed_value !== null && anomaly.observed_value !== undefined) && (
        <div
          style={{
            display: 'flex',
            gap: '16px',
            margin: '8px 0 10px 0',
            padding: '8px 12px',
            backgroundColor: '#FEF3C7',
            borderRadius: 'var(--radius-sm)',
            fontSize: 'var(--font-size-xs)',
          }}
        >
          <div>
            <span style={{ color: '#78350F', fontWeight: 600 }}>Observed Value: </span>
            <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#92400E' }}>
              {anomaly.observed_value}
            </span>
          </div>

          {anomaly.baseline_value !== null && anomaly.baseline_value !== undefined && (
            <div>
              <span style={{ color: '#78350F', fontWeight: 600 }}>
                {anomaly.baseline_type === 'OFFICIAL_TARGET'
                  ? 'Official Target: '
                  : (anomaly.baseline_type === 'HISTORICAL_BASELINE'
                    ? 'Historical Baseline: '
                    : 'Analytical Heuristic: ')}
              </span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#92400E' }}>
                {anomaly.baseline_value}
              </span>
            </div>
          )}

          {anomaly.deviation_value !== null && anomaly.deviation_value !== undefined && (
            <div>
              <span style={{ color: '#78350F', fontWeight: 600 }}>Deviation: </span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#B45309' }}>
                {anomaly.deviation_value > 0 ? `+${anomaly.deviation_value}` : anomaly.deviation_value}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Factual Explanation */}
      <p
        style={{
          margin: 0,
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-text-primary)',
          lineHeight: 1.5,
          fontWeight: 500,
        }}
      >
        {anomaly.explanation}
      </p>

      {/* Category Anomalies Breakdown (if any) */}
      {anomaly.category_anomalies && anomaly.category_anomalies.length > 0 && (
        <div style={{ marginTop: '10px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#78350F', marginBottom: '4px' }}>
            Outlier Categories ({anomaly.category_anomalies.length}):
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {anomaly.category_anomalies.map((cat, idx) => (
              <div
                key={idx}
                style={{
                  fontSize: '11px',
                  backgroundColor: '#FFF7ED',
                  border: '1px solid #FFEDD5',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  color: '#9A3412',
                }}
              >
                <strong>{cat.category_name}</strong>: {cat.observed_value} ({cat.deviation && cat.deviation > 0 ? `+${cat.deviation}` : cat.deviation})
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapsible Details & Governance Limitations */}
      <div style={{ marginTop: '10px', borderTop: '1px solid #FED7AA', paddingTop: '6px' }}>
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          style={{
            background: 'none',
            border: 'none',
            color: '#B45309',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 0',
          }}
          aria-expanded={showDetails}
        >
          <ShieldAlert size={12} />
          {showDetails ? 'Hide Governance Details' : 'View Detection Bounds & Scope'}
          {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {showDetails && (
          <div
            style={{
              marginTop: '6px',
              padding: '8px',
              backgroundColor: '#FFFBEB',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              color: '#78350F',
              lineHeight: 1.4,
            }}
          >
            <div><strong>Detection Method:</strong> {formatMethod(anomaly.method)}</div>
            <div><strong>Baseline Provenance:</strong> {formatBaselineType(anomaly.baseline_type) || 'None'}</div>
            {anomaly.limitations && <div><strong>Analytical Limitations:</strong> {anomaly.limitations}</div>}
            <div>
              <strong>Institutional Governance Note:</strong> Anomaly detection evaluates authorized query results against statistical distributions and configured analytical heuristics. Configured anomaly thresholds are analytical detection parameters unless an authoritative institutional target is present. It does not establish causality or official institutional policy violations.
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
