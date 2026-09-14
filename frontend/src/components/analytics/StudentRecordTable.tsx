import React, { useState } from 'react';
import { Users, ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card } from '../ui/Card';
import { StatusBadge } from '../common/StatusBadge';
import { Button } from '../ui/Button';
import { QueryResult } from '../../types';

interface StudentRecordTableProps {
  result: QueryResult;
  scope?: string | null;
  onPageChange?: (newPage: number) => void;
  isLoadingPage?: boolean;
}

export const StudentRecordTable: React.FC<StudentRecordTableProps> = ({
  result,
  scope,
  onPageChange,
  isLoadingPage = false,
}) => {
  const [localPage, setLocalPage] = useState<number>(result.metadata?.page || 1);
  const rows = result.rows || [];
  const columns = result.columns || [];
  const rowCount = result.row_count || rows.length;
  const page = result.metadata?.page || localPage;
  const pageSize = result.metadata?.page_size || 25;
  const hasMore = result.metadata?.has_more ?? (rowCount === pageSize);

  const handlePrev = () => {
    if (page > 1) {
      const p = page - 1;
      setLocalPage(p);
      if (onPageChange) onPageChange(p);
    }
  };

  const handleNext = () => {
    if (hasMore) {
      const p = page + 1;
      setLocalPage(p);
      if (onPageChange) onPageChange(p);
    }
  };

  // Friendly column header formatter
  const formatColumnHeader = (col: string): string => {
    const map: Record<string, string> = {
      roll_no: 'Roll No',
      register_no: 'Register No',
      admission_no: 'Admission No',
      full_name: 'Full Name',
      gender: 'Gender',
      primary_email: 'Institutional Email',
      department_code: 'Dept',
      department_name: 'Department',
      programme_code: 'Programme',
      programme_name: 'Programme Name',
      batch_label: 'Batch',
      section_code: 'Section',
      current_year_of_study: 'Year',
      status: 'Status',
      students_count: 'students',
    };
    return map[col.toLowerCase()] || col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Empty state if zero records returned
  if (rows.length === 0) {
    return (
      <Card style={{ padding: '32px 24px', textAlign: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: '#f1f5f9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-muted)',
            }}
          >
            <Users size={24} />
          </div>
          <div>
            <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)', margin: '0 0 4px 0' }}>
              No Matching Student Records Found
            </h3>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: 0, maxWidth: '460px' }}>
              No students were found in the authorized scope matching those filters.
            </p>
          </div>
          {scope && (
            <div style={{ marginTop: '4px' }}>
              <StatusBadge variant="neutral">Authorized Scope: {scope}</StatusBadge>
            </div>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflow: 'hidden' }}>
      {/* Header with Title and Scope Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(37, 99, 235, 0.1)',
              color: 'var(--color-brand-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Users size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-text-primary)', margin: 0 }}>
              Authorized Student Records
            </h3>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              Showing {rows.length} record{rows.length === 1 ? '' : 's'} on Page {page}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {scope && (
            <StatusBadge variant="info">
              <span>Scope: {scope}</span>
            </StatusBadge>
          )}
          <StatusBadge variant="neutral">
            <ShieldCheck size={13} style={{ marginRight: '4px' }} />
            <span>Read-Only PostgreSQL</span>
          </StatusBadge>
        </div>
      </div>

      {/* Accessible Student Records Table */}
      <div style={{ overflowX: 'auto', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 'var(--font-size-xs)',
            textAlign: 'left',
          }}
        >
          <thead>
            <tr style={{ backgroundColor: 'var(--color-bg-workspace)', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <th style={{ padding: '10px 12px', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', width: '40px' }}>
                #
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  style={{
                    padding: '10px 12px',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--color-text-secondary)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {formatColumnHeader(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr
                key={idx}
                style={{
                  borderBottom: idx === rows.length - 1 ? 'none' : '1px solid var(--color-border-subtle)',
                  backgroundColor: idx % 2 === 1 ? 'rgba(0, 0, 0, 0.015)' : '#ffffff',
                }}
              >
                <td style={{ padding: '10px 12px', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                  {(page - 1) * pageSize + idx + 1}
                </td>
                {columns.map((col) => {
                  const val = row[col];
                  const isRollNo = col.toLowerCase() === 'roll_no';
                  const isStatus = col.toLowerCase() === 'status';

                  return (
                    <td
                      key={col}
                      style={{
                        padding: '10px 12px',
                        color: 'var(--color-text-primary)',
                        whiteSpace: 'nowrap',
                        fontWeight: isRollNo ? 'var(--font-weight-medium)' : 'normal',
                        fontFamily: isRollNo ? 'monospace' : 'inherit',
                      }}
                    >
                      {isStatus ? (
                        <StatusBadge variant={val === 'ACTIVE' ? 'success' : 'neutral'}>
                          {val || 'N/A'}
                        </StatusBadge>
                      ) : val !== null && val !== undefined ? (
                        String(val)
                      ) : (
                        <span style={{ color: 'var(--color-text-muted)' }}>—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: '8px',
          borderTop: '1px solid var(--color-border-subtle)',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          Page {page} • Max {pageSize} per page
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Button
            type="button"
            variant="secondary"
            onClick={handlePrev}
            disabled={page <= 1 || isLoadingPage}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
          >
            <ChevronLeft size={14} />
            <span>Previous</span>
          </Button>

          <Button
            type="button"
            variant="secondary"
            onClick={handleNext}
            disabled={!hasMore || isLoadingPage}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
          >
            <span>Next</span>
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>
    </Card>
  );
};
