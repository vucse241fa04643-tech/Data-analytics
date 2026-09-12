import React, { useState } from 'react';
import { apiService } from '../../services/api';
import type { ExportFormat } from '../../types';
import { Download, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

interface ExportControlsProps {
  requestId: string;
  rowCount?: number;
  disabled?: boolean;
}

export const ExportControls: React.FC<ExportControlsProps> = ({
  requestId,
  rowCount,
  disabled = false,
}) => {
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const isExportDisabled = disabled || rowCount === 0 || !requestId;

  const handleExport = async (format: ExportFormat) => {
    if (isExportDisabled || exportingFormat) return;

    setError(null);
    setSuccessMsg(null);
    setExportingFormat(format);

    try {
      const { blob, filename } = await apiService.exportResult(requestId, format);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename || `agent63_export_${requestId.slice(0, 8)}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(url);

      setSuccessMsg(`Exported ${format.toUpperCase()} successfully.`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      console.error('Export failed:', err);
      setError(err?.message || `Failed to export as ${format.toUpperCase()}.`);
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        paddingTop: '12px',
        borderTop: '1px solid var(--color-border-subtle)',
        marginTop: '12px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-medium)',
            color: 'var(--color-text-secondary)',
          }}
        >
          <Download size={15} color="var(--color-brand-secondary)" />
          <span>
            Export Analytical Result{' '}
            {rowCount !== undefined &&
              (rowCount === 0
                ? '(0 rows — no records to export)'
                : `(${rowCount} row${rowCount === 1 ? '' : 's'})`)}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={() => handleExport('csv')}
            disabled={isExportDisabled || exportingFormat !== null}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              fontSize: '12px',
              fontWeight: 'var(--font-weight-medium)',
              backgroundColor: 'var(--color-bg-workspace)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              cursor: isExportDisabled || exportingFormat !== null ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
              opacity: isExportDisabled || exportingFormat !== null ? 0.5 : 1,
            }}
            title={rowCount === 0 ? 'No records available to export' : 'Download sanitized CSV spreadsheet'}
            onMouseOver={(e) => {
              if (!isExportDisabled && exportingFormat === null) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)';
                e.currentTarget.style.borderColor = 'var(--color-brand-secondary)';
                e.currentTarget.style.color = 'var(--color-brand-secondary)';
              }
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-workspace)';
              e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
              e.currentTarget.style.color = 'var(--color-text-primary)';
            }}
          >
            {exportingFormat === 'csv' ? (
              <span
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  border: '2px solid var(--color-brand-secondary)',
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                }}
              />
            ) : (
              <FileText size={13} color="var(--color-brand-secondary)" />
            )}
            <span>Export CSV</span>
          </button>

          <button
            type="button"
            onClick={() => handleExport('json')}
            disabled={isExportDisabled || exportingFormat !== null}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              fontSize: '12px',
              fontWeight: 'var(--font-weight-medium)',
              backgroundColor: 'var(--color-bg-workspace)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 'var(--radius-sm)',
              cursor: disabled || exportingFormat !== null ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
              opacity: disabled || exportingFormat !== null ? 0.6 : 1,
            }}
            title="Download structured JSON result"
            onMouseOver={(e) => {
              if (!disabled && exportingFormat === null) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)';
                e.currentTarget.style.borderColor = 'var(--color-brand-secondary)';
                e.currentTarget.style.color = 'var(--color-brand-secondary)';
              }
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-workspace)';
              e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
              e.currentTarget.style.color = 'var(--color-text-primary)';
            }}
          >
            {exportingFormat === 'json' ? (
              <span
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  border: '2px solid var(--color-brand-secondary)',
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                }}
              />
            ) : (
              <FileText size={13} color="var(--color-brand-secondary)" />
            )}
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            color: 'var(--color-danger)',
            backgroundColor: 'var(--color-danger-bg)',
            border: '1px solid var(--color-danger-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
          }}
        >
          <AlertCircle size={13} />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            color: 'var(--color-success)',
            backgroundColor: 'var(--color-success-bg)',
            border: '1px solid var(--color-success-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
          }}
        >
          <CheckCircle2 size={13} />
          <span>{successMsg}</span>
        </div>
      )}
    </div>
  );
};
export default ExportControls;
