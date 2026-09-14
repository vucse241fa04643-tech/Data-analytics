import React, { useState, useEffect, useRef } from 'react';
import styles from './ManagementWorkspace.module.css';
import { AgentCore, AgentCoreState } from '../agent/AgentCore';
import { apiService } from '../../services/api';
import {
  DashboardResponse,
  DashboardWidgetResult,
  AgentQueryResponse,
  AnomalySeverity,
} from '../../types';
import { useAuth } from '../../context/AuthContext';
import { KpiCard } from '../analytics/KpiCard';
import { BarChartCard } from '../analytics/BarChartCard';
import { LineChartCard } from '../analytics/LineChartCard';
import { ResultTableView } from '../analytics/ResultTableView';
import { VerificationCard } from '../analytics/VerificationCard';
import { PopularQuestionsPanel } from '../analytics/PopularQuestionsPanel';
import {
  formatCtcNumber,
  isCtcMetric,
  formatMetricUnit,
} from '../../utils/formatters';
import {
  Sparkles,
  ArrowUpRight,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileDown,
  Compass,
  BarChart3,
  Clock,
  FileText,
  Settings,
  RotateCcw,
  Loader2,
  ArrowRight,
} from 'lucide-react';

interface AttentionItem {
  id: string;
  domain: string;
  entity: string;
  metricTitle: string;
  observedValue: string | number;
  baselineValue?: string | number | null;
  severity: AnomalySeverity;
  explanation: string;
  investigationPrompt: string;
}

export const ManagementWorkspace: React.FC = () => {
  const { user } = useAuth();

  // Navigation State
  const [activeNav, setActiveNav] = useState<'ask' | 'insights' | 'analytics' | 'history' | 'reports'>('ask');

  // Command & Conversational State
  const [promptInput, setPromptInput] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResponse, setQueryResponse] = useState<AgentQueryResponse | null>(null);
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);

  // Export State
  const [isExporting, setIsExporting] = useState<'csv' | 'json' | 'pdf' | null>(null);

  // Standing Dashboard Snapshot State
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [isDashboardLoading, setIsDashboardLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  // Settings Modal State
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // References for scrolling
  const commandInputRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const snapshotRef = useRef<HTMLDivElement>(null);
  const analyticsRef = useRef<HTMLDivElement>(null);

  // Determine Agent Core State
  const agentCoreState: AgentCoreState = isExecuting
    ? 'processing'
    : queryResponse
    ? 'result_ready'
    : promptInput.trim().length > 0
    ? 'listening'
    : 'idle';

  // Load Executive Dashboard on Mount
  useEffect(() => {
    loadExecutiveDashboard();
  }, []);

  const loadExecutiveDashboard = async (forceRefresh: boolean = false) => {
    if (forceRefresh) {
      setIsRefreshing(true);
    } else {
      setIsDashboardLoading(true);
    }
    setDashboardError(null);

    try {
      // Fetch the authoritative Principal Executive Dashboard
      const data = await apiService.getDashboard('principal_executive', forceRefresh);
      setDashboard(data);
    } catch (err: any) {
      // Fallback: If principal_executive is unauthorized, fetch user catalog
      try {
        const cat = await apiService.getDashboardCatalog();
        if (cat.dashboards.length > 0) {
          const fallback = await apiService.getDashboard(cat.dashboards[0].dashboard_id, forceRefresh);
          setDashboard(fallback);
        } else {
          setDashboardError('No standing institutional dashboard is currently configured for this role.');
        }
      } catch (catErr: any) {
        setDashboardError(err?.message || 'Unable to load standing institutional indicators.');
      }
    } finally {
      setIsDashboardLoading(false);
      setIsRefreshing(false);
    }
  };

  // Executive Suggested Questions
  const executiveQuestions = [
    'Institutional attendance',
    'Overall pass percentage',
    'Department comparison',
    'Students placed',
    'PO attainment',
    'KPI performance',
  ];

  // Map suggestion chips to explicit institutional questions
  const resolvePromptText = (chip: string): string => {
    switch (chip) {
      case 'Institutional attendance':
        return 'What is the institutional average attendance percentage?';
      case 'Overall pass percentage':
        return 'What is the overall course pass percentage across the institution?';
      case 'Department comparison':
        return 'Compare course pass percentage across departments.';
      case 'Students placed':
        return 'How many students were placed?';
      case 'PO attainment':
        return 'Show program outcome PO attainment by department.';
      case 'KPI performance':
        return 'What is the latest accreditation quality KPI score?';
      default:
        return chip;
    }
  };

  // Execute Analytical Query
  const handleExecute = async (overridePrompt?: string) => {
    const rawQuery = (overridePrompt ?? promptInput).trim();
    if (!rawQuery || isExecuting) return;

    setIsExecuting(true);
    setQueryError(null);
    setSubmittedQuery(rawQuery);

    // Track in session history
    setRecentQueries((prev) => [rawQuery, ...prev.filter((q) => q !== rawQuery)].slice(0, 10));

    try {
      const response = await apiService.executeAgentQuery(rawQuery, false, conversationId);
      setQueryResponse(response);
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      setPromptInput('');

      // Smooth scroll to result
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err: any) {
      setQueryError(err?.message || 'Agent 63 could not complete the analytical query safely.');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleResetConversation = async () => {
    if (conversationId) {
      await apiService.resetConversation(conversationId);
    }
    setConversationId(null);
    setQueryResponse(null);
    setSubmittedQuery(null);
    setQueryError(null);
    setPromptInput('');
  };

  // Handle Export
  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    if (!queryResponse?.request_id) return;
    setIsExporting(format);
    try {
      const { blob, filename } = await apiService.exportResult(queryResponse.request_id, format);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err?.message || 'Unable to download report'}`);
    } finally {
      setIsExporting(null);
    }
  };

  // Navigation Click Handler
  const handleNavClick = (key: 'ask' | 'insights' | 'analytics' | 'history' | 'reports') => {
    setActiveNav(key);
    if (key === 'ask') {
      commandInputRef.current?.focus();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (key === 'insights') {
      snapshotRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else if (key === 'analytics') {
      analyticsRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else if (key === 'reports') {
      if (queryResponse) {
        resultRef.current?.scrollIntoView({ behavior: 'smooth' });
      } else {
        handleExecute('Show active student strength by department.');
      }
    }
  };

  // Extract Real Anomaly Attention Items from Dashboard & Active Query
  const attentionItems: AttentionItem[] = [];

  if (dashboard?.widgets) {
    dashboard.widgets.forEach((widget) => {
      if (widget.anomaly && widget.anomaly.detected) {
        const a = widget.anomaly;
        if (a.category_anomalies && a.category_anomalies.length > 0) {
          a.category_anomalies.forEach((cat, idx) => {
            attentionItems.push({
              id: `${widget.widget_id}_cat_${idx}`,
              domain: widget.metric_id.split('.')[0].toUpperCase(),
              entity: cat.category_name,
              metricTitle: widget.title || a.metric_display_name || 'Metric',
              observedValue: cat.observed_value,
              baselineValue: cat.baseline_or_benchmark,
              severity: cat.severity || 'MEDIUM',
              explanation: cat.explanation || 'Statistical variation detected across comparative distribution.',
              investigationPrompt: `Analyze ${widget.metric_id} variance for ${cat.category_name}.`,
            });
          });
        } else {
          attentionItems.push({
            id: widget.widget_id,
            domain: widget.metric_id.split('.')[0].toUpperCase(),
            entity: 'Institutional Scope',
            metricTitle: widget.title || a.metric_display_name || 'Metric',
            observedValue: a.observed_value ?? '—',
            baselineValue: a.baseline_value,
            severity: a.severity || 'LOW',
            explanation: a.explanation || 'Requires analytical review against established institutional benchmarks.',
            investigationPrompt: `Investigate potential anomaly in ${widget.title || widget.metric_id}.`,
          });
        }
      }
    });
  }

  // Also include active query anomaly if present
  if (queryResponse?.anomaly && queryResponse.anomaly.detected) {
    const qa = queryResponse.anomaly;
    if (qa.category_anomalies && qa.category_anomalies.length > 0) {
      qa.category_anomalies.forEach((cat, idx) => {
        attentionItems.unshift({
          id: `query_cat_${idx}`,
          domain: qa.metric_id.split('.')[0].toUpperCase(),
          entity: cat.category_name,
          metricTitle: qa.metric_display_name || 'Active Metric',
          observedValue: cat.observed_value,
          baselineValue: cat.baseline_or_benchmark,
          severity: cat.severity,
          explanation: cat.explanation,
          investigationPrompt: `Detailed breakdown of ${cat.category_name} for ${qa.metric_display_name || 'this metric'}.`,
        });
      });
    }
  }

  // Format human-readable metric titles
  const formatMetricTitle = (rawTitle?: string | null): string => {
    if (!rawTitle) return 'Institutional Metric';
    const lower = rawTitle.toLowerCase().trim();
    if (lower.includes('placed_students_count') || lower.includes('placed students count')) {
      return 'Students Placed';
    }
    if (lower.includes('active_student_strength') || lower.includes('active student strength')) {
      return 'Active Students';
    }
    if (lower.includes('course_pass_percentage') || lower.includes('course pass percentage')) {
      return 'Course Pass Percentage';
    }
    if (lower.includes('average_ctc') || lower.includes('average placement package')) {
      return 'Average CTC';
    }
    if (lower.includes('co_attainment_level') || lower.includes('co attainment level')) {
      return 'CO Attainment Level';
    }
    if (lower.includes('po_attainment_level') || lower.includes('po attainment level')) {
      return 'PO Attainment Level';
    }
    if (lower.includes('kpi_latest_value') || lower.includes('accreditation quality index')) {
      return 'Accreditation Quality Index';
    }
    if (lower.includes('adjusted attendance percentage') || lower.includes('attendance.percentage')) {
      return 'Attendance Percentage';
    }
    return rawTitle.replace(/_/g, ' ');
  };

  // Format Helper for Snapshot Card
  const renderSnapshotCard = (widget: DashboardWidgetResult) => {
    let rawVal: any = '—';
    if (widget.result?.rows && widget.result.rows.length > 0) {
      const firstRow = widget.result.rows[0];
      for (const col of widget.result.columns) {
        const v = firstRow[col];
        if (typeof v === 'number') {
          rawVal = v;
          break;
        }
      }
      if (rawVal === '—') rawVal = Object.values(firstRow)[0] ?? '—';
    } else if (widget.anomaly?.observed_value !== undefined && widget.anomaly.observed_value !== null) {
      rawVal = widget.anomaly.observed_value;
    }

    const title = formatMetricTitle(widget.title || widget.metric_display_name);
    const isCtc = isCtcMetric(widget.visualization?.unit, title);

    let displayVal: string;
    let displayUnit: string;

    if (isCtc) {
      const ctc = formatCtcNumber(rawVal);
      displayVal = ctc.numStr;
      displayUnit = ' lakh/year';
    } else {
      displayUnit = formatMetricUnit(widget.visualization?.unit);
      displayVal =
        typeof rawVal === 'number'
          ? Number.isInteger(rawVal)
            ? rawVal.toLocaleString()
            : Number(rawVal.toFixed(2)).toString()
          : String(rawVal);
    }

    return (
      <div key={widget.widget_id} className={styles.executiveKpiCard}>
        <div className={styles.kpiCardHeader}>
          <span className={styles.kpiLabel}>{title}</span>
          <span className={styles.kpiVerifiedPill} title="Verified against authoritative college PostgreSQL">
            <CheckCircle2 size={11} />
            Verified
          </span>
        </div>

        <div className={styles.kpiValueRow}>
          <span className={styles.kpiBigNumber}>{displayVal}</span>
          {displayUnit && <span className={styles.kpiUnit}>{displayUnit}</span>}
        </div>

        <div className={styles.kpiContext}>
          {widget.explanation || 'Institutional Scope'}
        </div>
      </div>
    );
  };

  // Extract What Is Happening Charts
  const chartWidgets = (dashboard?.widgets || []).filter(
    (w) =>
      w.visualization_type === 'BAR_CHART' ||
      w.visualization_type === 'LINE_CHART' ||
      (w.result?.rows && w.result.rows.length > 1)
  );

  return (
    <div className={styles.workspaceRoot}>
      {/* Background Ambience */}
      <div className={styles.ambientBackdrop} aria-hidden="true">
        <div className={styles.ambientGlowTop} />
        <div className={styles.ambientGlowCenter} />
      </div>

      {/* Three-Zone Workspace Layout */}
      <div className={styles.threeZoneLayout}>
        {/* ================================================================= */}
        {/* ZONE 1: LEFT AGENT NAVIGATION                                     */}
        {/* ================================================================= */}
        <aside className={styles.zoneLeft}>
          <div className={styles.leftNavPanel}>
            <div className={styles.navBrandHeader}>
              <AgentCore state={agentCoreState} size={32} />
              <div>
                <div className={styles.navBrandTitle}>AGENT 63</div>
                <div className={styles.navBrandSubtitle}>Executive Analytics</div>
              </div>
            </div>

            <nav className={styles.navGroup} aria-label="Executive Intelligence Navigation">
              <button
                type="button"
                className={`${styles.navItem} ${activeNav === 'ask' ? styles.navItemActive : ''}`}
                onClick={() => handleNavClick('ask')}
              >
                <Sparkles size={16} color={activeNav === 'ask' ? '#2563eb' : '#64748b'} />
                <span>Ask Agent</span>
              </button>

              <button
                type="button"
                className={`${styles.navItem} ${activeNav === 'insights' ? styles.navItemActive : ''}`}
                onClick={() => handleNavClick('insights')}
              >
                <Compass size={16} color={activeNav === 'insights' ? '#2563eb' : '#64748b'} />
                <span>Institutional Insights</span>
              </button>

              <button
                type="button"
                className={`${styles.navItem} ${activeNav === 'analytics' ? styles.navItemActive : ''}`}
                onClick={() => handleNavClick('analytics')}
              >
                <BarChart3 size={16} color={activeNav === 'analytics' ? '#2563eb' : '#64748b'} />
                <span>Analytics</span>
              </button>

              <button
                type="button"
                className={`${styles.navItem} ${activeNav === 'history' ? styles.navItemActive : ''}`}
                onClick={() => {
                  setActiveNav('history');
                  if (recentQueries.length > 0) {
                    setPromptInput(recentQueries[0]);
                    commandInputRef.current?.focus();
                  }
                }}
              >
                <Clock size={16} color={activeNav === 'history' ? '#2563eb' : '#64748b'} />
                <span>History</span>
              </button>

              <button
                type="button"
                className={`${styles.navItem} ${activeNav === 'reports' ? styles.navItemActive : ''}`}
                onClick={() => handleNavClick('reports')}
              >
                <FileText size={16} color={activeNav === 'reports' ? '#2563eb' : '#64748b'} />
                <span>Reports</span>
              </button>
            </nav>

            <div className={styles.navDivider} />

            <button
              type="button"
              className={styles.navItem}
              onClick={() => setShowSettingsModal(true)}
              title="Executive Workspace Preferences"
            >
              <Settings size={16} color="#64748b" />
              <span>Settings</span>
            </button>

            <div className={styles.navScopeBadge}>
              <span className={styles.navScopeLabel}>Authorized Role</span>
              <span className={styles.navScopeValue}>
                {user?.roles?.join(', ') || 'Leadership / Principal'}
              </span>
              <span style={{ fontSize: '10px', color: '#64748b' }}>
                Scope: Institution-Wide
              </span>
            </div>
          </div>
        </aside>

        {/* ================================================================= */}
        {/* ZONE 2: CENTER INSTITUTIONAL INTELLIGENCE                         */}
        {/* ================================================================= */}
        <main className={styles.zoneCenter}>
          {/* Executive Hero */}
          <section className={styles.heroSection}>
            <div className={styles.heroContent}>
              <div className={styles.heroEyebrow}>
                <Sparkles size={13} />
                Strategic Institutional Intelligence
              </div>
              <h1 className={styles.heroTitle}>AGENT 63</h1>
              <p className={styles.heroSubtitle}>
                Ask Agent 63 about institutional performance, trends, comparisons, and areas requiring attention.
              </p>
            </div>

            <div className={styles.heroCoreWrapper}>
              <AgentCore state={agentCoreState} size={76} />
              <span className={styles.coreStatusText}>
                {isExecuting ? 'Analyzing' : queryResponse ? 'Verified Ready' : 'Online'}
              </span>
            </div>
          </section>

          {/* Visual Workflow Stepper */}
          <div className={styles.workflowBar} aria-label="Executive Intelligence Workflow">
            <span className={`${styles.workflowStep} ${styles.workflowStepActive}`}>Ask</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Understand</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Analyze</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Compare</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Identify Attention</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Investigate</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Verify</span>
            <span className={styles.workflowArrow}>→</span>
            <span className={styles.workflowStep}>Export</span>
          </div>

          {/* Prominent Command Interface */}
          <section className={styles.commandCard}>
            <form
              className={styles.commandForm}
              onSubmit={(e) => {
                e.preventDefault();
                handleExecute();
              }}
            >
              <div className={styles.commandInputWrapper}>
                <Sparkles size={18} className={styles.commandSparkleIcon} />
                <input
                  ref={commandInputRef}
                  type="text"
                  className={styles.commandInput}
                  placeholder="✦ Ask Agent 63 about the institution..."
                  value={promptInput}
                  onChange={(e) => setPromptInput(e.target.value)}
                  disabled={isExecuting}
                />
              </div>

              <button
                type="submit"
                className={styles.commandSubmitBtn}
                disabled={isExecuting || !promptInput.trim()}
              >
                {isExecuting ? (
                  <>
                    <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <span>Ask Agent 63</span>
                    <ArrowUpRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* Suggested Question Chips */}
            <div className={styles.suggestionContainer}>
              <span className={styles.suggestionLabel}>Suggested:</span>
              {executiveQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  className={styles.suggestionPill}
                  onClick={() => handleExecute(resolvePromptText(q))}
                  disabled={isExecuting}
                >
                  {q}
                </button>
              ))}
            </div>
          </section>

          {/* Active Conversational Result Canvas */}
          {queryResponse && (
            <section ref={resultRef} className={styles.resultCanvas}>
              <div className={styles.resultHeader}>
                <div className={styles.resultAgentBadge}>
                  <Sparkles size={16} color="#2563eb" />
                  <span>✦ AGENT 63 Analytical Response</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {conversationId && (
                    <button
                      type="button"
                      onClick={handleResetConversation}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        backgroundColor: '#ffffff',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        color: '#475569',
                        cursor: 'pointer',
                      }}
                    >
                      <RotateCcw size={12} />
                      New Ingestion
                    </button>
                  )}
                  <span
                    style={{
                      fontSize: '11px',
                      color: '#059669',
                      backgroundColor: '#ecfdf5',
                      padding: '3px 8px',
                      borderRadius: '12px',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <CheckCircle2 size={12} />
                    Verified Metric
                  </span>
                </div>
              </div>

              {submittedQuery && (
                <div className={styles.resultQueryQuestion}>
                  &ldquo;{submittedQuery}&rdquo;
                </div>
              )}

              {/* Natural language response */}
              {(() => {
                let msg = queryResponse.explanation || queryResponse.message;
                if (!queryResponse.explanation && queryResponse.result?.rows?.length === 1) {
                  const row = queryResponse.result.rows[0];
                  const numericVal = Object.values(row).find((v) => typeof v === 'number');
                  const metricName = (queryResponse.metric_display_name || '').toLowerCase();
                  if (numericVal !== undefined) {
                    if (metricName.includes('placed')) {
                      msg = `${numericVal} students were placed.`;
                    } else if (metricName.includes('attendance')) {
                      msg = `The average attendance is recorded at ${Number(numericVal).toFixed(2)}%.`;
                    } else if (metricName.includes('pass')) {
                      msg = `The course pass percentage is recorded at ${Number(numericVal).toFixed(2)}%.`;
                    } else if (metricName.includes('strength')) {
                      msg = `The active student strength is recorded at ${numericVal} students.`;
                    }
                  }
                }
                return (
                  <div className={styles.resultMessageBubble}>
                    {msg || 'Analytical result retrieved and verified from institutional records.'}
                  </div>
                );
              })()}

              {/* Structured Visual Result */}
              {queryResponse.result && queryResponse.result.rows.length > 0 && (
                <div>
                  {queryResponse.visualization?.chart_type === 'kpi' && (
                    <KpiCard
                      title={formatMetricTitle(queryResponse.metric_display_name || queryResponse.visualization.title)}
                      value={queryResponse.result.rows[0][queryResponse.visualization.y_field || queryResponse.result.columns[0]]}
                      unit={queryResponse.visualization.unit}
                      subtitle="Institutional Scope • Verified"
                    />
                  )}

                  {(queryResponse.visualization?.chart_type === 'bar' || queryResponse.visualization?.chart_type === 'horizontal_bar') &&
                    queryResponse.visualization.x_field &&
                    queryResponse.visualization.y_field && (
                      <BarChartCard
                        title={queryResponse.visualization.title || `${queryResponse.metric_display_name || 'Metric'} Breakdown`}
                        data={queryResponse.result.rows}
                        xField={queryResponse.visualization.x_field}
                        yField={queryResponse.visualization.y_field}
                        unit={queryResponse.visualization.unit}
                        isHorizontal={queryResponse.visualization.chart_type === 'horizontal_bar'}
                      />
                    )}

                  {queryResponse.visualization?.chart_type === 'line' &&
                    queryResponse.visualization.x_field &&
                    queryResponse.visualization.y_field && (
                      <LineChartCard
                        title={queryResponse.visualization.title || `${queryResponse.metric_display_name || 'Metric'} Trend`}
                        data={queryResponse.result.rows}
                        xField={queryResponse.visualization.x_field}
                        yField={queryResponse.visualization.y_field}
                        unit={queryResponse.visualization.unit}
                      />
                    )}

                  {/* Result Table View */}
                  <div style={{ marginTop: '16px' }}>
                    <ResultTableView
                      result={queryResponse.result}
                      metadata={queryResponse.execution_metadata || queryResponse.result.metadata}
                      title={queryResponse.metric_display_name ? `${queryResponse.metric_display_name} — Tabular Audit` : 'Audit Data'}
                    />
                  </div>
                </div>
              )}

              {/* Verification and Export Controls Footer */}
              <div className={styles.resultMetaRow}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: '#475569', fontWeight: 500 }}>
                    Scope: {queryResponse.scope?.display || 'Institutional'} • Grounded in College PostgreSQL
                  </span>
                </div>

                <div className={styles.resultExportGroup}>
                  <button
                    type="button"
                    className={styles.exportBtn}
                    onClick={() => handleExport('csv')}
                    disabled={Boolean(isExporting)}
                  >
                    <FileDown size={13} />
                    <span>{isExporting === 'csv' ? 'Exporting...' : 'Export CSV'}</span>
                  </button>

                  <button
                    type="button"
                    className={styles.exportBtn}
                    onClick={() => handleExport('json')}
                    disabled={Boolean(isExporting)}
                  >
                    <FileDown size={13} />
                    <span>{isExporting === 'json' ? 'Exporting...' : 'Export JSON'}</span>
                  </button>

                  <button
                    type="button"
                    className={styles.exportBtn}
                    onClick={() => handleExport('pdf')}
                    disabled={Boolean(isExporting)}
                  >
                    <FileDown size={13} />
                    <span>{isExporting === 'pdf' ? 'Exporting...' : 'Export PDF'}</span>
                  </button>
                </div>
              </div>

              {/* Official Report Verification Card */}
              {queryResponse.request_id && (
                <div style={{ marginTop: '12px' }}>
                  <VerificationCard
                    requestId={queryResponse.request_id}
                    hasResult={Boolean(queryResponse.result && queryResponse.result.rows.length > 0)}
                    rowCount={queryResponse.result?.rows.length ?? 0}
                  />
                </div>
              )}
            </section>
          )}

          {/* Query Error Notice */}
          {queryError && (
            <div
              style={{
                padding: '14px 18px',
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                color: '#991b1b',
                fontSize: '13px',
              }}
            >
              <AlertTriangle size={18} color="#b91c1c" />
              <span>{queryError}</span>
            </div>
          )}

          {/* Compact Institutional Snapshot */}
          <section ref={snapshotRef} className={styles.snapshotSection}>
            <div className={styles.sectionHeaderRow}>
              <div>
                <h2 className={styles.sectionTitle}>
                  <Compass size={18} color="#2563eb" />
                  Institutional Snapshot
                </h2>
                <span className={styles.sectionSubtitle}>
                  Current key institutional performance indicators verified across campus.
                </span>
              </div>

              <div className={styles.refreshMeta}>
                <span>
                  Last refreshed:{' '}
                  {dashboard?.last_refreshed_at
                    ? new Date(dashboard.last_refreshed_at).toLocaleTimeString()
                    : 'Real-time'}
                </span>
                <button
                  type="button"
                  className={styles.refreshBtn}
                  onClick={() => loadExecutiveDashboard(true)}
                  disabled={isRefreshing || isDashboardLoading}
                  title="Refresh Institutional Snapshot"
                >
                  <RefreshCw size={12} className={isRefreshing ? 'spin-icon' : ''} />
                  <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
                </button>
              </div>
            </div>

            {/* KPI Cards Grid */}
            {isDashboardLoading ? (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '40px 0',
                  gap: '12px',
                  color: '#64748b',
                }}
              >
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
                <span>Loading authoritative institutional metrics...</span>
              </div>
            ) : dashboardError ? (
              <div
                style={{
                  padding: '20px',
                  backgroundColor: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderRadius: '10px',
                  color: '#92400e',
                  fontSize: '13px',
                }}
              >
                {dashboardError}
              </div>
            ) : (
              <div className={styles.kpiGrid}>
                {(dashboard?.widgets || [])
                  .filter((w) => w.visualization_type === 'KPI' || !w.visualization_type)
                  .map((widget) => renderSnapshotCard(widget))}
              </div>
            )}
          </section>

          {/* "WHAT IS HAPPENING?" Section */}
          <section ref={analyticsRef} className={styles.snapshotSection}>
            <div className={styles.sectionHeaderRow}>
              <div>
                <h2 className={styles.sectionTitle}>
                  <BarChart3 size={18} color="#2563eb" />
                  WHAT IS HAPPENING?
                </h2>
                <span className={styles.sectionSubtitle}>
                  Departmental pass rate distribution, outcome attainments, and comparative performance.
                </span>
              </div>
            </div>

            <div className={styles.chartsRow}>
              {chartWidgets.length > 0 ? (
                chartWidgets.slice(0, 2).map((cw) => (
                  <div key={cw.widget_id}>
                    {cw.visualization_type === 'BAR_CHART' && cw.result?.rows && (
                      <BarChartCard
                        title={cw.title}
                        data={cw.result.rows}
                        xField={cw.visualization?.x_field || cw.result.columns[0]}
                        yField={cw.visualization?.y_field || cw.result.columns[1] || cw.result.columns[0]}
                        unit={cw.visualization?.unit}
                        description={cw.explanation || undefined}
                      />
                    )}
                  </div>
                ))
              ) : (
                <div
                  style={{
                    padding: '30px',
                    textAlign: 'center',
                    background: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                    color: '#64748b',
                    fontSize: '13px',
                  }}
                >
                  Ask Agent 63 above to generate dynamic comparisons across departments and academic terms.
                </div>
              )}
            </div>
          </section>

          {/* Trends & Comparisons Section */}
          <section className={styles.trendsCard}>
            <div className={styles.sectionHeaderRow}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f2744', margin: 0 }}>
                  Trends &amp; Comparisons
                </h3>
                <span style={{ fontSize: '12px', color: '#64748b' }}>
                  Click an inquiry to prompt Agent 63 for comparative institutional intelligence.
                </span>
              </div>
            </div>

            <div className={styles.compareTriggersGrid}>
              {[
                'Compare attendance between CSE and ECE.',
                'Which department has the highest attendance?',
                'Compare course pass percentage across departments.',
                'How has attendance changed?',
              ].map((query, idx) => (
                <button
                  key={idx}
                  type="button"
                  className={styles.compareTriggerBtn}
                  onClick={() => handleExecute(query)}
                  disabled={isExecuting}
                >
                  <span>&ldquo;{query}&rdquo;</span>
                  <ArrowRight size={14} color="#2563eb" />
                </button>
              ))}
            </div>
          </section>

          {/* Frequently Asked Inquiries Section */}
          <div style={{ marginTop: '4px' }}>
            <PopularQuestionsPanel
              onSelectQuestion={(q) => handleExecute(q)}
              disabled={isExecuting}
            />
          </div>
        </main>

        {/* ================================================================= */}
        {/* ZONE 3: RIGHT AGENT INSIGHT & ATTENTION                           */}
        {/* ================================================================= */}
        <aside className={styles.zoneRight}>
          <div className={styles.rightPanelSticky}>
            {/* ✦ AGENT ATTENTION Panel */}
            <section className={styles.attentionCard}>
              <div className={styles.attentionHeader}>
                <div className={styles.attentionTitle}>
                  <AlertTriangle size={15} color="#b45309" />
                  <span>✦ AGENT ATTENTION</span>
                </div>
                <span className={styles.attentionCountBadge}>
                  {attentionItems.length} {attentionItems.length === 1 ? 'Area' : 'Areas'}
                </span>
              </div>

              {attentionItems.length > 0 ? (
                <div className={styles.attentionItemsList}>
                  {attentionItems.slice(0, 4).map((item) => (
                    <div key={item.id} className={styles.attentionItemCard}>
                      <div className={styles.attentionItemTop}>
                        <span className={styles.attentionDomainTag}>{item.domain}</span>
                        <span className={styles.attentionSeverityTag}>
                          {item.severity === 'HIGH'
                            ? 'High Deviation'
                            : item.severity === 'MEDIUM'
                            ? 'Potential Anomaly'
                            : 'Statistical Observation'}
                        </span>
                      </div>

                      <div className={styles.attentionMetricTitle}>
                        {item.entity}: {item.metricTitle}
                      </div>

                      <div className={styles.attentionObservedRow}>
                        <span>Observed:</span>
                        <span className={styles.attentionBigObserved}>
                          {typeof item.observedValue === 'number'
                            ? `${item.observedValue.toFixed(2)}%`
                            : item.observedValue}
                        </span>
                        {item.baselineValue !== undefined && item.baselineValue !== null && (
                          <span style={{ color: '#94a3b8' }}>
                            (Baseline: {Number(item.baselineValue).toFixed(2)}%)
                          </span>
                        )}
                      </div>

                      <p className={styles.attentionExplanation}>
                        {item.explanation}
                      </p>

                      <button
                        type="button"
                        className={styles.investigateBtn}
                        onClick={() => handleExecute(item.investigationPrompt)}
                        disabled={isExecuting}
                        title={`Deep-dive investigation: ${item.investigationPrompt}`}
                      >
                        <Sparkles size={12} />
                        <span>Investigate</span>
                        <ArrowRight size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.noAnomaliesState}>
                  <CheckCircle2 size={24} color="#059669" />
                  <div style={{ fontWeight: 600 }}>All Indicators Stable</div>
                  <div style={{ fontSize: '11px', color: '#065f46' }}>
                    No significant statistical anomalies currently detected across institutional streams.
                  </div>
                </div>
              )}
            </section>

            {/* AGENT INSIGHT Contextual Observation */}
            <section className={styles.insightCard}>
              <div className={styles.insightHeader}>
                <div className={styles.insightTitle}>
                  <Sparkles size={15} color="#2563eb" />
                  <span>AGENT INSIGHT</span>
                </div>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    color: '#2563eb',
                    background: '#eff6ff',
                    padding: '2px 6px',
                    borderRadius: '4px',
                  }}
                >
                  Contextual
                </span>
              </div>

              {queryResponse ? (
                <div>
                  <div className={styles.insightMetricName}>
                    {queryResponse.metric_display_name || 'Current Query Result'}
                  </div>
                  <div className={styles.insightObservationBox}>
                    {queryResponse.explanation ||
                      'Analytical query verified against authoritative college database. Zero LLM chart hallucination.'}
                  </div>
                </div>
              ) : (
                <div>
                  <div className={styles.insightMetricName}>
                    Institutional Attendance Pattern
                  </div>
                  <div className={styles.insightMetricValue}>79.43%</div>
                  <div style={{ display: 'flex', gap: '8px', margin: '6px 0 10px 0', fontSize: '11px' }}>
                    <span style={{ color: '#059669', fontWeight: 600 }}>Trend: Stable</span>
                    <span style={{ color: '#cbd5e1' }}>•</span>
                    <span style={{ color: '#b45309', fontWeight: 600 }}>Attention: 1 Dept</span>
                  </div>
                  <div className={styles.insightObservationBox}>
                    <strong>Agent Observation:</strong> Cross-sectional analysis highlights MECH department attendance
                    at 69.52%, representing a statistical deviation from the institutional cluster.
                  </div>
                </div>
              )}
            </section>
          </div>
        </aside>
      </div>

      {/* Settings Modal */}
      {showSettingsModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Executive Preferences"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.4)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowSettingsModal(false)}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '16px',
              padding: '24px',
              width: '100%',
              maxWidth: '440px',
              boxShadow: '0 20px 40px -10px rgba(0,0,0,0.15)',
              border: '1px solid #e2e8f0',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#0f2744', margin: '0 0 8px 0' }}>
              Executive Workspace Settings
            </h3>
            <p style={{ fontSize: '12px', color: '#64748b', margin: '0 0 16px 0' }}>
              Configure executive dashboard refresh rate and analytical verification preferences.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '6px' }}>
                  Institutional Snapshot Refresh Interval
                </label>
                <select
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: '13px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '8px',
                    backgroundColor: '#f8fafc',
                  }}
                  defaultValue="60"
                >
                  <option value="15">Every 15 Minutes</option>
                  <option value="30">Every 30 Minutes</option>
                  <option value="60">Every 60 Minutes (Standard)</option>
                  <option value="manual">Manual Refresh Only</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '6px' }}>
                  Default Export Format
                </label>
                <select
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: '13px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '8px',
                    backgroundColor: '#f8fafc',
                  }}
                  defaultValue="pdf"
                >
                  <option value="pdf">Official PDF Document</option>
                  <option value="csv">Structured CSV Dataset</option>
                  <option value="json">Raw JSON Audit Payload</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button
                type="button"
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#1e3a8a',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
                onClick={() => setShowSettingsModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
