import React, { useState } from 'react';
import { apiService } from '../../services/api';
import type { VerificationResult, VerificationStatus } from '../../types';
import { ShieldCheck, CheckCircle2, AlertTriangle, HelpCircle, FileCheck2, AlertCircle } from 'lucide-react';
import { formatMetricValueWithUnit } from '../../utils/formatters';

interface VerificationCardProps {
  requestId: string;
  documentId?: string;
  hasResult?: boolean;
  rowCount?: number;
}

export const VerificationCard: React.FC<VerificationCardProps> = ({
  requestId,
  documentId,
  hasResult = true,
  rowCount,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isUnavailable = !hasResult || rowCount === 0 || !requestId;

  const handleVerify = async () => {
    if (isUnavailable || loading) return;
    setLoading(true);
    setError(null);

    try {
      const res = await apiService.verifyResult(requestId, documentId);
      setResult(res);
    } catch (err: any) {
      console.error('Verification failed:', err);
      const msg = err?.message || 'Verification could not be performed.';
      if (msg.toLowerCase().includes('not found') || msg.toLowerCase().includes('expired')) {
        setError('Analytical result is not available in the active session. Please re-run the query.');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeConfig = (status: VerificationStatus) => {
    switch (status) {
      case 'MATCH':
        return {
          bg: 'var(--color-success-bg)',
          border: 'var(--color-success-border)',
          color: 'var(--color-success)',
          icon: <CheckCircle2 size={13} />,
          label: 'MATCH',
        };
      case 'MISMATCH':
        return {
          bg: 'var(--color-warning-bg)',
          border: 'var(--color-warning-border)',
          color: 'var(--color-warning)',
          icon: <AlertTriangle size={13} />,
          label: 'MISMATCH',
        };
      case 'NOT_COMPARABLE':
        return {
          bg: 'var(--color-info-bg)',
          border: 'var(--color-info-border)',
          color: 'var(--color-info)',
          icon: <HelpCircle size={13} />,
          label: 'NOT COMPARABLE',
        };
      case 'NOT_VERIFIED':
      default:
        return {
          bg: 'var(--color-bg-subtle)',
          border: 'var(--color-border-subtle)',
          color: 'var(--color-text-muted)',
          icon: <HelpCircle size={13} />,
          label: 'NOT VERIFIED',
        };
    }
  };

  return (
    <div
      style={{
        marginTop: '12px',
        padding: '12px 16px',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--color-bg-workspace)',
        border: '1px solid var(--color-border-subtle)',
        fontSize: 'var(--font-size-xs)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={16} color="var(--color-brand-primary)" />
          <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
            Official Report Verification
          </span>
        </div>

        {isUnavailable ? (
          <span style={{ color: 'var(--color-text-muted)', fontSize: '11px', fontStyle: 'italic' }}>
            {rowCount === 0
              ? 'Not available — zero analytical records returned for reconciliation.'
              : 'Not available — execute an analytical query with results first.'}
          </span>
        ) : !result && (
          <button
            type="button"
            onClick={handleVerify}
            disabled={loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              fontSize: '12px',
              fontWeight: 'var(--font-weight-medium)',
              backgroundColor: 'var(--color-brand-primary)',
              color: 'var(--color-text-inverse)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.15s ease',
              opacity: loading ? 0.7 : 1,
            }}
            onMouseOver={(e) => {
              if (!loading) e.currentTarget.style.backgroundColor = 'var(--color-brand-primary-hover)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-brand-primary)';
            }}
          >
            {loading ? (
              <>
                <span
                  style={{
                    display: 'inline-block',
                    width: '12px',
                    height: '12px',
                    border: '2px solid white',
                    borderTopColor: 'transparent',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                  }}
                />
                <span>Comparing...</span>
              </>
            ) : (
              <span>Verify Against Official Records</span>
            )}
          </button>
        )}
      </div>

      {error && (
        <div
          style={{
            marginTop: '8px',
            padding: '6px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--color-danger-bg)',
            border: '1px solid var(--color-danger-border)',
            color: 'var(--color-danger)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
          }}
        >
          <AlertCircle size={13} />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Status Badge & Reason */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {(() => {
              const cfg = getStatusBadgeConfig(result.status);
              return (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: cfg.bg,
                    border: `1px solid ${cfg.border}`,
                    color: cfg.color,
                    fontSize: '11px',
                    fontWeight: 'var(--font-weight-semibold)',
                  }}
                >
                  {cfg.icon}
                  <span>{cfg.label}</span>
                </span>
              );
            })()}
            <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-xs)' }}>
              {result.reason}
            </span>
          </div>

          {/* Value Comparison Cards */}
          {(result.analytical_value !== undefined || result.official_value !== undefined) && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '10px',
                padding: '10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block' }}>
                  Query Result (Live Analytical)
                </span>
                <span
                  style={{
                    fontFamily: 'var(--font-family-mono)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {formatMetricValueWithUnit(result.analytical_value, result.unit, { title: result.metric_display_name })}
                </span>
              </div>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block' }}>
                  Official Record (Authoritative KPI)
                </span>
                <span
                  style={{
                    fontFamily: 'var(--font-family-mono)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {formatMetricValueWithUnit(result.official_value, result.unit, { title: result.metric_display_name })}
                </span>
              </div>
            </div>
          )}

          {/* Document Reference */}
          {result.document_reference && (
            <div
              style={{
                fontSize: '11px',
                color: 'var(--color-text-secondary)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <FileCheck2 size={13} color="var(--color-brand-secondary)" />
              <span style={{ color: 'var(--color-text-muted)' }}>Registered Document: </span>
              <span style={{ fontWeight: 'var(--font-weight-medium)', color: 'var(--color-text-primary)' }}>
                {result.document_reference.title ||
                  result.document_reference.document_number ||
                  result.document_reference.document_id}
              </span>
              {result.document_reference.version && (
                <span style={{ color: 'var(--color-text-muted)' }}>
                  (v{result.document_reference.version})
                </span>
              )}
            </div>
          )}

          {/* Mandatory Governance Disclaimer */}
          <div
            style={{
              fontSize: '10px',
              fontStyle: 'italic',
              color: 'var(--color-text-muted)',
              paddingTop: '6px',
              borderTop: '1px solid var(--color-border-subtle)',
              lineHeight: 1.4,
            }}
          >
            {result.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
};
export default VerificationCard;
