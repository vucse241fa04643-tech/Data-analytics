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
import { ResultTableView } from '../components/analytics/ResultTableView';
import { QueryDetailsAccordion } from '../components/analytics/QueryDetailsAccordion';
import {
  MessageSquare,
  Send,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  Loader2,
  Lock,
  BarChart2,
  Info,
  RotateCcw,
  HelpCircle,
} from 'lucide-react';

export const AgentPage: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [isDryRun, setIsDryRun] = useState(false);
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [queryResponse, setQueryResponse] = useState<AgentQueryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

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
      domain: 'Attainment Trend',
      prompt: 'What is the course pass percentage trend over academic years?',
    },
  ];

  const handleResetConversation = async () => {
    if (conversationId) {
      await apiService.resetConversation(conversationId);
    }
    setConversationId(null);
    setQueryResponse(null);
    setSubmittedQuestion(null);
    setErrorMessage(null);
    setErrorCode(null);
    setInputValue('');
  };

  const handleSubmit = async (e?: React.FormEvent, overridePrompt?: string) => {
    if (e) e.preventDefault();
    const query = (overridePrompt ?? inputValue).trim();
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
      const response = await apiService.executeAgentQuery(query, isDryRun, conversationId);
      setQueryResponse(response);
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      setInputValue('');
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.errorCode === 'DATABASE_NOT_CONFIGURED') {
          setErrorMessage('College database is currently unavailable.');
        } else if (err.statusCode === 400 || err.errorCode === 'INTENT_REJECTED') {
          setErrorMessage('Your query could not be validated safely.');
        } else {
          setErrorMessage(err.message || 'Agent 63 could not complete the query safely.');
        }
        setErrorCode(err.errorCode || 'API_ERROR');
      } else {
        setErrorMessage('Agent 63 could not complete the query safely.');
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
  const viz = queryResponse?.visualization;
  const explanation = queryResponse?.explanation;
  const metricDisplayName = queryResponse?.metric_display_name || viz?.title;
  const metricId = metadata?.metric_id || queryResponse?.intent?.metric_id;

  // Extract scope for display
  const scopeValue = (() => {
    if (!queryResponse?.intent?.filters) return null;
    const f = queryResponse.intent.filters;
    const entries = Object.entries(f).filter(([k, v]) => v !== null && k !== 'is_active');
    if (entries.length === 0) return 'Institutional';
    return entries.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(', ');
  })();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)', minHeight: '100%' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-primary)', margin: 0 }}>
              Agent 63 Conversational Analytics
            </h1>
            <StatusBadge variant="success">Phase 10 Conversational Analytics</StatusBadge>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', margin: 0 }}>
            Multi-turn follow-up analytics, contextual dimension inheritance, deterministic visualization, and read-only PostgreSQL.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {conversationId && (
            <Button
              type="button"
              variant="secondary"
              onClick={handleResetConversation}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', padding: '6px 12px' }}
            >
              <RotateCcw size={13} />
              <span>New Conversation</span>
            </Button>
          )}
          <StatusBadge variant="neutral">
            <ShieldCheck size={14} style={{ marginRight: '4px' }} />
            <span>Zero Authorization Reuse • Fresh AST SQL • Read-Only DB</span>
          </StatusBadge>
        </div>
      </div>

      {/* Main Conversational & Results Canvas */}
      <Card style={{ flex: 1, minHeight: '560px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', padding: 'var(--spacing-sm) 0' }}>
          {/* State 1: Loading State */}
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
                gap: '16px',
              }}
            >
              <Loader2 size={40} color="var(--color-brand-primary)" style={{ animation: 'spin 1s linear infinite' }} />
              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)', margin: 0 }}>
                  Running secure institutional query…
                </p>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '8px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                  <span>1. Resolving Intent &amp; Context</span>
                  <span>•</span>
                  <span>2. Compiling Safe SQL</span>
                  <span>•</span>
                  <span>3. Retrieving Validated Result</span>
                </div>
              </div>
            </div>
          )}

          {/* State 2: Controlled Error Notification */}
          {!isLoading && errorMessage && (
            <div style={{ padding: '0 var(--spacing-md)' }}>
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
                      ? 'College Database Unavailable'
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

          {/* State 3: Execution Response (Phase 9/10 Hierarchy) */}
          {!isLoading && queryResponse && (
            <div style={{ padding: '0 var(--spacing-sm)', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* 1. QUERY Title Banner & Trace Header */}
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
                  {queryResponse.is_follow_up && (
                    <StatusBadge variant="info">Follow-up Query • Context Inherited</StatusBadge>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {queryResponse.dry_run && <StatusBadge variant="warning">Dry Run Mode</StatusBadge>}
                  {queryResponse.request_id && (
                    <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                      Trace: {queryResponse.request_id.slice(0, 8)}
                    </span>
                  )}
                  {conversationId && (
                    <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                      Session: {conversationId.slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>

              {/* Clarification Questions (if present) */}
              {queryResponse.clarification_questions && queryResponse.clarification_questions.length > 0 && (
                <div
                  style={{
                    padding: '12px 16px',
                    backgroundColor: '#f0f9ff',
                    border: '1px solid #bae6fd',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: '#0369a1' }}>
                    <HelpCircle size={15} />
                    <span>Suggested Follow-up Clarifications:</span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {queryResponse.clarification_questions.map((cq, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSubmit(undefined, cq)}
                        style={{
                          fontSize: 'var(--font-size-xs)',
                          padding: '4px 10px',
                          backgroundColor: '#ffffff',
                          border: '1px solid #7dd3fc',
                          borderRadius: 'var(--radius-full)',
                          color: '#0369a1',
                          cursor: 'pointer',
                        }}
                      >
                        {cq}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 2 & 3. RESULT SUMMARY & APPROPRIATE VISUALIZATION */}
              {viz && result && (
                <div>
                  {viz.chart_type === 'kpi' && result.rows.length > 0 && (
                    <KpiCard
                      title={viz.title || metricDisplayName || 'Institutional Metric'}
                      value={result.rows[0][viz.y_field || result.columns[0]]}
                      unit={viz.unit}
                      description={viz.description}
                      subtitle={scopeValue ? `Scope: ${scopeValue}` : undefined}
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

                  {/* Visualization Unavailable Banner if chart_type is table or none for non-empty results */}
                  {!viz.recommended && result.status === 'SUCCESS' && result.rows.length > 0 && (
                    <div
                      style={{
                        padding: '10px 14px',
                        backgroundColor: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <Info size={16} color="var(--color-brand-secondary)" />
                      <span>
                        Visualization is not available for this result shape. Full tabular data is presented below.
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* 4. ANALYTICAL SUMMARY */}
              {explanation && (
                <AnalyticalSummaryCard explanation={explanation} />
              )}

              {/* 5. RESULT TABLE (Universal Accessible Representation) */}
              {result && (
                <ResultTableView
                  result={result}
                  metadata={metadata}
                  title={metricDisplayName ? `${metricDisplayName} — Tabular Records` : 'Result Table'}
                />
              )}

              {/* 6. QUERY DETAILS & AUDIT ACCORDION */}
              <QueryDetailsAccordion
                metricId={metricId}
                metricDisplayName={metricDisplayName}
                scope={scopeValue}
                requestId={queryResponse.request_id}
                sqlArtifact={sqlArtifact}
                metadata={metadata}
              />
            </div>
          )}

          {/* State 4: Initial Clean State */}
          {!isLoading && !errorMessage && !queryResponse && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--spacing-xl) 0' }}>
              <EmptyState
                icon={<BarChart2 size={36} color="var(--color-brand-primary)" />}
                title="Institutional Analytics Engine Ready"
                description="Ask an institutional question in plain English. Agent 63 compiles AST-validated SQL, executes against PostgreSQL, and deterministically generates KPIs, charts, analytical summaries, and audited tables."
                action={
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: 0 }}>
                      Deterministic visualizations: KPI Cards • Bar Charts • Line Series • Fully Accessible Data Tables.
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                      <ShieldCheck size={14} color="var(--color-brand-secondary)" />
                      <span>Zero LLM chart hallucinations • Strict read-only database isolation</span>
                    </div>
                  </div>
                }
              />
            </div>
          )}
        </div>

        {/* Bottom Section: Query Input & Example Chips */}
        <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: 'var(--spacing-md)', marginTop: 'auto' }}>
          {/* Example Query Chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
            <Sparkles size={14} color="var(--color-brand-secondary)" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', color: 'var(--color-text-secondary)' }}>
              Institutional Analytics Queries:
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
            {exampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setInputValue(q.prompt)}
                style={{
                  fontSize: 'var(--font-size-xs)',
                  padding: '6px 12px',
                  backgroundColor: 'var(--color-bg-workspace)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-full)',
                  color: 'var(--color-text-primary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)';
                  e.currentTarget.style.borderColor = 'var(--color-brand-secondary)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-workspace)';
                  e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                }}
              >
                <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-brand-primary)' }}>
                  [{q.domain}]
                </span>
                <span>{q.prompt}</span>
              </button>
            ))}
          </div>

          {/* Form Input Area */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask an analytical question (e.g., 'What is the average attendance percentage for CSE students?')..."
                disabled={isLoading}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  fontSize: 'var(--font-size-sm)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  outline: 'none',
                  backgroundColor: 'var(--color-bg-surface)',
                  color: 'var(--color-text-primary)',
                }}
              />
              <Button
                type="submit"
                variant="primary"
                disabled={isLoading || !inputValue.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 18px' }}
              >
                {isLoading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={16} />}
                <span>Execute</span>
              </Button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-text-muted)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={isDryRun}
                  onChange={(e) => setIsDryRun(e.target.checked)}
                  disabled={isLoading}
                />
                <span>Dry run mode (compile &amp; validate SQL without database execution)</span>
              </label>

              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                Press Enter to execute • Governed by RBAC
              </span>
            </div>
          </form>
        </div>
      </Card>
    </div>
  );
};
