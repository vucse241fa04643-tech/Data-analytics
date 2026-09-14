import React from 'react';
import { Card } from '../ui/Card';
import { StatusBadge } from '../common/StatusBadge';
import { Table, Clock, Layers } from 'lucide-react';
import { ExecutionMetadata, QueryResult } from '../../types';
import { formatColumnHeader, formatCtcNumber } from '../../utils/formatters';

interface ResultTableViewProps {
  result: QueryResult;
  metadata?: ExecutionMetadata | null;
  title?: string;
}

export const ResultTableView: React.FC<ResultTableViewProps> = ({
  result,
  metadata,
  title = 'Result Table',
}) => {
  const isNumericValue = (val: any) => {
    return typeof val === 'number';
  };

  const getHeaderLabel = (col: string) => {
    const clean = col.toLowerCase().trim();
    if (clean === 'students_count') {
      return 'students';
    }
    if (clean === 'metric_value') {
      if (title.toLowerCase().includes('attendance')) {
        return 'Attendance (%)';
      }
      if (title.toLowerCase().includes('ctc') || title.toLowerCase().includes('package')) {
        return 'CTC (₹ lakh/year)';
      }
      return 'Metric Value';
    }
    return formatColumnHeader(col);
  };

  const formatCellValue = (val: any, col: string) => {
    if (val === null) {
      return <em style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>NULL</em>;
    }
    const isNum = isNumericValue(val);
    if (isNum) {
      const colClean = col.toLowerCase();
      if (colClean.includes('ctc') || (title.toLowerCase().includes('ctc') && colClean === 'metric_value')) {
        return formatCtcNumber(val).fullStr;
      }
      const formatted = Number.isInteger(val) ? val.toLocaleString() : Number(val.toFixed(2)).toString();
      if (title.toLowerCase().includes('attendance') && (colClean === 'metric_value' || colClean.includes('pct') || colClean.includes('percent'))) {
        return `${formatted}%`;
      }
      return formatted;
    }
    const str = String(val);
    if (str.includes('students_count')) {
      return str.replace(/students_count/g, 'students');
    }
    return str;
  };

  return (
    <Card
      role="region"
      aria-label="Tabular query results"
      style={{
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--color-bg-surface)',
        boxShadow: 'var(--shadow-card)',
        overflow: 'hidden',
      }}
    >
      {/* Table Header / Stats Bar */}
      <div
        style={{
          padding: '12px 16px',
          backgroundColor: 'var(--color-bg-workspace)',
          borderBottom: '1px solid var(--color-border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Table size={16} color="var(--color-brand-secondary)" />
          <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-text-primary)' }}>
            {title}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
          {metadata && (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={12} /> {metadata.execution_time_ms.toFixed(1)} ms
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Layers size={12} /> {result.row_count} rows
              </span>
            </>
          )}
          <StatusBadge
            variant={
              result.status === 'SUCCESS'
                ? 'success'
                : result.status === 'EMPTY'
                ? 'neutral'
                : 'warning'
            }
          >
            {result.status}
          </StatusBadge>
        </div>
      </div>

      {/* Empty State */}
      {result.status === 'EMPTY' || result.rows.length === 0 ? (
        <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          No matching institutional records were found for this query.
        </div>
      ) : (
        /* Accessible Scrollable Table Container */
        <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: 'var(--font-size-xs)',
              textAlign: 'left',
            }}
          >
            <caption style={{ display: 'none' }}>Institutional Query Results</caption>
            <thead>
              <tr style={{ backgroundColor: 'var(--color-bg-workspace)', borderBottom: '1px solid var(--color-border-subtle)' }}>
                {result.columns.map((col) => {
                  // Determine alignment based on sample value
                  const isNum = result.rows.some((r) => isNumericValue(r[col]));
                  return (
                    <th
                      key={col}
                      scope="col"
                      style={{
                        padding: '10px 14px',
                        fontWeight: 'var(--font-weight-semibold)',
                        color: 'var(--color-text-primary)',
                        textTransform: 'uppercase',
                        fontSize: '11px',
                        letterSpacing: '0.04em',
                        textAlign: isNum ? 'right' : 'left',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {getHeaderLabel(col)}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  style={{
                    borderBottom: '1px solid var(--color-border-subtle)',
                    backgroundColor: rIdx % 2 === 0 ? 'var(--color-bg-surface)' : 'var(--color-bg-workspace)',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  {result.columns.map((col, cIdx) => {
                    const val = row[col];
                    const isNum = isNumericValue(val);

                    return (
                      <td
                        key={col}
                        scope={cIdx === 0 ? 'row' : undefined}
                        style={{
                          padding: '10px 14px',
                          color: val === null ? 'var(--color-text-muted)' : 'var(--color-text-primary)',
                          textAlign: isNum ? 'right' : 'left',
                          fontFamily: isNum ? 'var(--font-family-mono, monospace)' : 'inherit',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {formatCellValue(val, col)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
