import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { apiService, ApiError } from '../services/api';
import { AgentQueryResponse } from '../types';
import {
  MessageSquare,
  Send,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Loader2,
  Lock,
  Code2,
  Clock,
  Layers,
  Table,
} from 'lucide-react';

export const AgentPage: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [isDryRun, setIsDryRun] = useState(false);
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [queryResponse, setQueryResponse] = useState<AgentQueryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  // Authoritative approved semantic catalog metrics
  const exampleQuestions = [
    {
      domain: 'Attendance',
      prompt: 'What is the average attendance percentage for CSE students?',
    },
    {
      domain: 'Performance',
      prompt: 'Compare course pass percentage between CSE and ECE for academic year 2024–2025.',
    },
    {
      domain: 'Student Strength',
      prompt: 'Show active student strength by department.',
    },
    {
      domain: 'Placements',
      prompt: 'Show the number of placed students by department.',
    },
  ];

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = inputValue.trim();
    if (!query || isLoading) return;

    // Check authentication token existence
    const token = apiService.getAuthToken();
    if (!token) {
      setSubmittedQuestion(query);
      setQueryResponse(null);
      setErrorCode('AUTHENTICATION_REQUIRED');
      setErrorMessage('Institutional authentication required. Please sign in with institutional credentials.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setErrorCode(null);
    setSubmittedQuestion(query);
    setQueryResponse(null);

    try {
      const response = await apiService.executeAgentQuery(query, isDryRun);
      setQueryResponse(response);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        setErrorCode(err.errorCode || 'API_ERROR');
      } else {
        setErrorMessage('Unable to communicate with the Agent 63 backend service.');
        setErrorCode('NETWORK_ERROR');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenSignIn = () => {
    window.dispatchEvent(new Event('agent63_open_auth'));
  };

  const result = queryResponse?.result;
  const sqlArtifact = queryResponse?.sql_artifact;
  const metadata = queryResponse?.execution_metadata || result?.metadata;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)', minHeight: '100%' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-primary)' }}>
              Agent 63 Analytical Query Engine
            </h1>
            <StatusBadge variant="success">Phase 8 Safe SQL Execution</StatusBadge>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Natural-language to verified read-only SQL execution and validated result delivery.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusBadge variant="neutral">
            <ShieldCheck size={14} style={{ marginRight: '4px' }} />
            <span>Read-Only Execution • AST Verified • Parameter Separated</span>
          </StatusBadge>
        </div>
      </div>

      {/* Main Conversation & Results Canvas */}
      <Card style={{ flex: 1, minHeight: '520px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', padding: 'var(--spacing-sm) 0' }}>
          {/* State 1: Loading */}
          {isLoading && (
            <div
              role="status"
              aria-live="polite"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 'var(--spacing-2xl) 0',
                gap: '12px',
              }}
            >
              <Loader2 size={36} color="var(--color-brand-primary)" style={{ animation: 'spin 1s linear infinite' }} />
              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)', margin: 0 }}>
                  Agent 63 is processing your analytical query...
                </p>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '4px', margin: 0 }}>
                  Interpreting intent, compiling safe SQL, and executing read-only database query.
                </p>
              </div>
            </div>
          )}

          {/* State 2: Error Notification */}
          {!isLoading && errorMessage && (
            <div style={{ padding: '0 var(--spacing-lg)' }}>
              <div
                style={{
                  padding: '16px',
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                }}
              >
                <AlertCircle size={20} color="#b91c1c" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1 }}>
                  <h4 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: '#991b1b', margin: '0 0 4px 0' }}>
                    {errorCode === 'AUTHENTICATION_REQUIRED'
                      ? 'Authentication Required'
                      : errorCode === 'FORBIDDEN'
                      ? 'Authorization Denied'
                      : errorCode === 'DATABASE_NOT_CONFIGURED'
                      ? 'Institutional Database Unconfigured'
                      : errorCode === 'DATABASE_TIMEOUT'
                      ? 'Database Query Timed Out'
                      : 'Analytical Query Notice'}
                  </h4>
                  <p style={{ fontSize: 'var(--font-size-xs)', color: '#b91c1c', margin: '0 0 8px 0', lineHeight: 1.5 }}>
                    {errorMessage}
                  </p>

                  {errorCode === 'AUTHENTICATION_REQUIRED' && (
                    <button
                      type="button"
                      onClick={handleOpenSignIn}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        backgroundColor: 'var(--color-brand-primary)',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--font-size-xs)',
                        fontWeight: 'var(--font-weight-medium)',
                        cursor: 'pointer',
                      }}
                    >
                      <Lock size={12} />
                      Sign In with Institutional Account
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* State 3: Execution Response */}
          {!isLoading && queryResponse && (
            <div style={{ padding: '0 var(--spacing-sm)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Question Banner */}
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: 'var(--color-bg-workspace)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <MessageSquare size={16} color="var(--color-brand-primary)" />
                  <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-medium)', color: 'var(--color-text-primary)' }}>
                    &ldquo;{submittedQuestion}&rdquo;
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {queryResponse.dry_run && <StatusBadge variant="warning">Dry Run Mode</StatusBadge>}
                  {queryResponse.request_id && (
                    <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                      Trace: {queryResponse.request_id.slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>

              {/* Informational Message Banner if Present */}
              {queryResponse.message && (
                <div style={{ padding: '8px 12px', backgroundColor: 'var(--color-bg-workspace)', borderRadius: 'var(--radius-sm)', fontSize: '12px', color: 'var(--color-text-secondary)', borderLeft: '3px solid var(--color-brand-primary)' }}>
                  {queryResponse.message}
                </div>
              )}

              {/* SQL Artifact Container (Read-Only Inspection) */}
              {sqlArtifact && (
                <div
                  style={{
                    border: '1px solid var(--color-border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--color-bg-surface)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      padding: '10px 16px',
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
                      <Code2 size={16} color="var(--color-brand-primary)" />
                      <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-brand-primary)' }}>
                        Compiled SQL Artifact (Deterministic &amp; Parameterized)
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <StatusBadge variant="neutral">Read-Only</StatusBadge>
                      <StatusBadge variant="success">AST Validated</StatusBadge>
                    </div>
                  </div>

                  <div style={{ padding: '12px 16px', backgroundColor: '#0f172a', color: '#f8fafc', overflowX: 'auto' }}>
                    <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '12px', lineHeight: 1.5 }}>
                      {sqlArtifact.sql}
                    </pre>
                  </div>

                  {sqlArtifact.parameters && Object.keys(sqlArtifact.parameters).length > 0 && (
                    <div style={{ padding: '8px 16px', backgroundColor: 'var(--color-bg-workspace)', borderTop: '1px solid var(--color-border-subtle)', fontSize: '11px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 'bold', color: 'var(--color-text-secondary)' }}>Bound Parameters:</span>
                      {Object.entries(sqlArtifact.parameters).map(([k, v]) => (
                        <span key={k} style={{ fontFamily: 'monospace', color: 'var(--color-brand-primary)' }}>
                          :{k} = {JSON.stringify(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Execution Results Section */}
              {result && (
                <div
                  style={{
                    border: '1px solid var(--color-border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--color-bg-surface)',
                    boxShadow: 'var(--shadow-card)',
                    overflow: 'hidden',
                  }}
                >
                  {/* Results Header */}
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
                        Execution Result Set
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                      {metadata && (
                        <>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Clock size={12} /> {metadata.execution_time_ms} ms
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Layers size={12} /> {result.row_count} rows
                          </span>
                        </>
                      )}
                      <StatusBadge variant={result.status === 'SUCCESS' ? 'success' : result.status === 'EMPTY' ? 'neutral' : 'warning'}>
                        {result.status}
                      </StatusBadge>
                    </div>
                  </div>

                  {/* Empty Results Case */}
                  {result.status === 'EMPTY' && (
                    <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                      Query executed successfully but returned 0 rows for the specified filters and organizational grain.
                    </div>
                  )}

                  {/* Successful Results Table */}
                  {result.status === 'SUCCESS' && result.rows.length > 0 && (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-xs)', textAlign: 'left' }}>
                        <thead>
                          <tr style={{ backgroundColor: 'var(--color-bg-workspace)', borderBottom: '1px solid var(--color-border-subtle)' }}>
                            {result.columns.map((col) => (
                              <th
                                key={col}
                                style={{
                                  padding: '10px 14px',
                                  fontWeight: 'var(--font-weight-semibold)',
                                  color: 'var(--color-text-primary)',
                                  textTransform: 'uppercase',
                                  fontSize: '11px',
                                  letterSpacing: '0.04em',
                                }}
                              >
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result.rows.map((row, rIdx) => (
                            <tr
                              key={rIdx}
                              style={{
                                borderBottom: '1px solid var(--color-border-subtle)',
                                backgroundColor: rIdx % 2 === 0 ? 'var(--color-bg-surface)' : 'var(--color-bg-workspace)',
                              }}
                            >
                              {result.columns.map((col) => {
                                const val = row[col];
                                return (
                                  <td
                                    key={col}
                                    style={{
                                      padding: '10px 14px',
                                      color: val === null ? 'var(--color-text-muted)' : 'var(--color-text-primary)',
                                      fontFamily: typeof val === 'number' ? 'monospace' : 'inherit',
                                    }}
                                  >
                                    {val === null ? (
                                      <em style={{ color: 'var(--color-text-muted)' }}>NULL</em>
                                    ) : (
                                      String(val)
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Unconfigured / Error Status Inside Result */}
                  {result.status === 'DATABASE_NOT_CONFIGURED' && (
                    <div style={{ padding: '16px', backgroundColor: '#fffbeb', color: '#92400e', fontSize: 'var(--font-size-xs)' }}>
                      Institutional database is not currently configured. SQL query was safely generated and validated.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* State 4: Initial Clean State */}
          {!isLoading && !errorMessage && !queryResponse && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--spacing-xl) 0' }}>
              <EmptyState
                icon={<MessageSquare size={32} />}
                title="Agent 63 Analytical Query Engine Ready"
                description="Ask an institutional analytics question. Phase 8 securely compiles and validates read-only SQL, executing against PostgreSQL with full parameter isolation and result validation."
                action={
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: 0 }}>
                      Supports attendance percentage, course pass rates, active student strength, outcomes, placements, and more.
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                      <ShieldCheck size={14} color="var(--color-brand-secondary)" />
                      <span>AST-validated queries • Statement timeouts • Strict read-only transactions</span>
                    </div>
                  </div>
                }
              />
            </div>
          )}
        </div>

        {/* Example Query Chips */}
        <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: 'var(--spacing-md)', marginTop: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
            <Sparkles size={14} color="var(--color-brand-primary)" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Approved Analytical Queries
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '8px' }}>
            {exampleQuestions.map((q, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--color-bg-workspace)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-text-secondary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  cursor: 'pointer',
                  transition: 'border-color var(--transition-fast)',
                }}
                onClick={() => setInputValue(q.prompt)}
                title="Click to populate input placeholder"
              >
                <span style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--color-brand-primary)', fontSize: '10px' }}>
                  [{q.domain}]
                </span>
                <span style={{ lineHeight: 1.4 }}>{q.prompt}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Input Area */}
        <form onSubmit={handleSubmit} style={{ marginTop: 'var(--spacing-md)' }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask Agent 63 an institutional analytics question..."
                disabled={isLoading}
                style={{
                  width: '100%',
                  padding: '12px var(--spacing-md)',
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-strong)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-sm)',
                  outline: 'none',
                }}
                aria-label="Institutional analytics question"
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              <input
                type="checkbox"
                checked={isDryRun}
                onChange={(e) => setIsDryRun(e.target.checked)}
                disabled={isLoading}
              />
              <span>Dry Run (SQL Only)</span>
            </label>

            <Button
              type="submit"
              variant="primary"
              disabled={isLoading || !inputValue.trim()}
              rightIcon={isLoading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={16} />}
              title="Execute analytical query"
            >
              Ask Agent 63
            </Button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px' }}>
            <HelpCircle size={12} color="var(--color-text-muted)" />
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              Full analytical execution pipeline active. Read-only transactions enforce institutional security.
            </span>
          </div>
        </form>
      </Card>
    </div>
  );
};
