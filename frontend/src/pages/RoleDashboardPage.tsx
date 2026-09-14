import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import {
  DashboardCatalogItem,
  DashboardResponse,
  DashboardScheduleItem,
  DashboardWidgetResult,
} from '../types';
import { Card } from '../components/ui/Card';
import { KpiCard } from '../components/analytics/KpiCard';
import { BarChartCard } from '../components/analytics/BarChartCard';
import { LineChartCard } from '../components/analytics/LineChartCard';
import { ResultTableView } from '../components/analytics/ResultTableView';
import { AnomalyInsightCard } from '../components/analytics/AnomalyInsightCard';
import { useAuth } from '../context/AuthContext';
import { formatScopeDisplay } from '../utils/formatters';
import {
  RefreshCw,
  Calendar,
  Shield,
  Clock,
  AlertTriangle,
  Layers,
  Trash2,
  X,
  Info,
} from 'lucide-react';

export const RoleDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [catalog, setCatalog] = useState<DashboardCatalogItem[]>([]);
  const [activeDashboardId, setActiveDashboardId] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Schedules Modal State
  const [showScheduleModal, setShowScheduleModal] = useState<boolean>(false);
  const [schedules, setSchedules] = useState<DashboardScheduleItem[]>([]);
  const [scheduleInterval, setScheduleInterval] = useState<number>(60);
  const [scheduleSubmitting, setScheduleSubmitting] = useState<boolean>(false);
  const [scheduleMessage, setScheduleMessage] = useState<string | null>(null);

  // Load Catalog on mount
  useEffect(() => {
    loadCatalog();
  }, []);

  // Load Dashboard when activeDashboardId changes
  useEffect(() => {
    if (activeDashboardId) {
      loadDashboard(activeDashboardId);
    }
  }, [activeDashboardId]);

  const loadCatalog = async () => {
    setLoading(true);
    setError(null);
    try {
      const catResp = await apiService.getDashboardCatalog();
      setCatalog(catResp.dashboards);
      if (catResp.dashboards.length > 0) {
        setActiveDashboardId(catResp.active_dashboard_id || catResp.dashboards[0].dashboard_id);
      } else {
        setLoading(false);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to resolve institutional dashboard catalog.');
      setLoading(false);
    }
  };

  const loadDashboard = async (dashboardId: string, forceRefresh: boolean = false) => {
    if (forceRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await apiService.getDashboard(dashboardId, forceRefresh);
      setDashboard(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load institutional dashboard data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadSchedules = async () => {
    try {
      const list = await apiService.getDashboardSchedules();
      setSchedules(list);
    } catch (err: any) {
      setScheduleMessage(err?.message || 'Failed to load schedules.');
    }
  };

  const handleCreateSchedule = async () => {
    if (!activeDashboardId) return;
    setScheduleSubmitting(true);
    setScheduleMessage(null);
    try {
      await apiService.createDashboardSchedule(activeDashboardId, scheduleInterval);
      setScheduleMessage('Schedule created successfully.');
      await loadSchedules();
    } catch (err: any) {
      setScheduleMessage(err?.message || 'Failed to create schedule.');
    } finally {
      setScheduleSubmitting(false);
    }
  };

  const handleCancelSchedule = async (scheduleId: string) => {
    try {
      await apiService.cancelDashboardSchedule(scheduleId);
      await loadSchedules();
    } catch (err: any) {
      setScheduleMessage(err?.message || 'Failed to cancel schedule.');
    }
  };

  const openScheduleManager = () => {
    setShowScheduleModal(true);
    setScheduleMessage(null);
    loadSchedules();
  };

  // Helper to extract metric value for KPI widget
  const getKpiValue = (widget: DashboardWidgetResult): number | string => {
    if (widget.result && widget.result.rows && widget.result.rows.length > 0) {
      const firstRow = widget.result.rows[0];
      const cols = widget.result.columns;
      // Look for metric column
      for (const col of cols) {
        const val = firstRow[col];
        if (typeof val === 'number') return val;
      }
      return Object.values(firstRow)[0] ?? '—';
    }
    if (widget.anomaly?.observed_value !== undefined && widget.anomaly.observed_value !== null) {
      return widget.anomaly.observed_value;
    }
    return '—';
  };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: 'var(--spacing-md)' }}>
      {/* 1. Header Banner */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: 'var(--spacing-lg)',
          backgroundColor: '#FFFFFF',
          padding: 'var(--spacing-lg)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-subtle)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Shield size={22} color="#1E3A8A" />
            <h1
              style={{
                margin: 0,
                fontSize: 'var(--font-size-xl)',
                fontWeight: 'var(--font-weight-bold)',
                color: '#0F172A',
              }}
            >
              {dashboard ? dashboard.title : 'Institutional Role Dashboard'}
            </h1>
            {dashboard?.scope?.display && (
              <span
                style={{
                  backgroundColor: '#EFF6FF',
                  color: '#1E40AF',
                  border: '1px solid #BFDBFE',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 600,
                }}
              >
                {formatScopeDisplay(dashboard.scope.display, user?.roles, dashboard.scope.scope_type)}
              </span>
            )}
          </div>
          <p
            style={{
              margin: 0,
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            {dashboard?.description || 'Server-controlled role-based institutional intelligence.'}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {dashboard && (
            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', textAlign: 'right' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={12} />
                <span>Refreshed: {new Date(dashboard.last_refreshed_at).toLocaleTimeString()}</span>
              </div>
              <span style={{ textTransform: 'uppercase', fontSize: '10px', color: '#64748B' }}>
                Mode: {dashboard.refresh_mode}
              </span>
            </div>
          )}

          <button
            onClick={() => activeDashboardId && loadDashboard(activeDashboardId, true)}
            disabled={refreshing || loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#2563EB',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: refreshing || loading ? 'not-allowed' : 'pointer',
              opacity: refreshing || loading ? 0.7 : 1,
            }}
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh Now'}</span>
          </button>

          <button
            onClick={openScheduleManager}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#F1F5F9',
              color: '#334155',
              border: '1px solid #CBD5E1',
              borderRadius: 'var(--radius-sm)',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Calendar size={14} />
            <span>Schedules</span>
          </button>
        </div>
      </div>

      {/* 2. Multi-Dashboard Role Tabs (If user holds multiple authorized dashboards) */}
      {catalog.length > 1 && (
        <div
          style={{
            display: 'flex',
            gap: '8px',
            marginBottom: 'var(--spacing-md)',
            borderBottom: '1px solid var(--color-border-subtle)',
            paddingBottom: '8px',
          }}
        >
          {catalog.map((item) => {
            const isActive = item.dashboard_id === activeDashboardId;
            return (
              <button
                key={item.dashboard_id}
                onClick={() => setActiveDashboardId(item.dashboard_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: isActive ? '#1E3A8A' : '#F8FAFC',
                  color: isActive ? '#FFFFFF' : '#475569',
                  border: '1px solid',
                  borderColor: isActive ? '#1E3A8A' : '#E2E8F0',
                  borderRadius: 'var(--radius-sm)',
                  padding: '6px 12px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Layers size={14} />
                <span>{item.title}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div
          style={{
            backgroundColor: '#FEF2F2',
            border: '1px solid #FCA5A5',
            color: '#991B1B',
            padding: '12px 16px',
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--spacing-md)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Partial Failure Notice */}
      {dashboard?.refresh_status === 'PARTIAL_FAILURE' && (
        <div
          style={{
            backgroundColor: '#FFFBEB',
            border: '1px solid #FCD34D',
            color: '#92400E',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--spacing-md)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '13px',
          }}
        >
          <Info size={16} />
          <span>One or more analytical widgets are currently unavailable due to database connectivity.</span>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--color-text-muted)' }}>
          <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 12px auto', display: 'block' }} />
          <p style={{ margin: 0, fontSize: 'var(--font-size-md)' }}>Loading institutional dashboard analytics...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && catalog.length === 0 && (
        <Card style={{ padding: '40px', textAlign: 'center' }}>
          <Shield size={36} color="#64748B" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ margin: '0 0 8px 0', color: '#1E293B' }}>No Role Dashboards Available</h3>
          <p style={{ margin: 0, color: '#64748B', fontSize: '14px' }}>
            Your institutional account does not currently hold permissions for configured analytics dashboards.
          </p>
        </Card>
      )}

      {/* 3. Dashboard Content */}
      {!loading && dashboard && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
          {/* Section A: KPI Metric Cards Grid */}
          {dashboard.widgets.some((w) => w.visualization_type === 'KPI') && (
            <div>
              <h3
                style={{
                  fontSize: 'var(--font-size-md)',
                  fontWeight: 700,
                  color: '#0F172A',
                  margin: '0 0 12px 0',
                }}
              >
                Key Institutional Indicators
              </h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: 'var(--spacing-md)',
                }}
              >
                {dashboard.widgets
                  .filter((w) => w.visualization_type === 'KPI')
                  .map((widget) => {
                    if (widget.status === 'UNAVAILABLE' || widget.status === 'ERROR') {
                      return (
                        <Card
                          key={widget.widget_id}
                          style={{
                            padding: 'var(--spacing-md)',
                            backgroundColor: '#F8FAFC',
                            border: '1px solid #E2E8F0',
                            borderRadius: 'var(--radius-md)',
                          }}
                        >
                          <div style={{ fontSize: '12px', color: '#64748B', marginBottom: '4px' }}>
                            {widget.title}
                          </div>
                          <div style={{ fontSize: '14px', fontWeight: 600, color: '#94A3B8' }}>
                            Data Unavailable
                          </div>
                          <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '6px' }}>
                            {widget.error_message || 'Database unconfigured.'}
                          </div>
                        </Card>
                      );
                    }

                    return (
                      <KpiCard
                        key={widget.widget_id}
                        title={widget.title}
                        value={getKpiValue(widget)}
                        unit={widget.visualization?.unit}
                        subtitle={widget.metric_display_name}
                        description={widget.explanation || undefined}
                      />
                    );
                  })}
              </div>
            </div>
          )}

          {/* Section B: Visual Charts & Analytics Section */}
          {dashboard.widgets.some((w) => w.visualization_type !== 'KPI') && (
            <div>
              <h3
                style={{
                  fontSize: 'var(--font-size-md)',
                  fontWeight: 700,
                  color: '#0F172A',
                  margin: '0 0 12px 0',
                }}
              >
                Comparative Visual Analytics
              </h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
                  gap: 'var(--spacing-lg)',
                }}
              >
                {dashboard.widgets
                  .filter((w) => w.visualization_type !== 'KPI')
                  .map((widget) => {
                    if (widget.status === 'UNAVAILABLE' || widget.status === 'ERROR' || !widget.result) {
                      return (
                        <Card
                          key={widget.widget_id}
                          style={{
                            padding: 'var(--spacing-lg)',
                            backgroundColor: '#F8FAFC',
                            border: '1px solid #E2E8F0',
                            borderRadius: 'var(--radius-md)',
                          }}
                        >
                          <h4 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#1E293B' }}>
                            {widget.title}
                          </h4>
                          <p style={{ margin: 0, color: '#64748B', fontSize: '13px' }}>
                            {widget.error_message || 'Data unavailable for this breakdown.'}
                          </p>
                        </Card>
                      );
                    }

                    if (
                      widget.visualization?.chart_type === 'bar' ||
                      widget.visualization?.chart_type === 'horizontal_bar'
                    ) {
                      return (
                        <BarChartCard
                          key={widget.widget_id}
                          title={widget.title}
                          data={widget.result.rows}
                          xField={widget.visualization.x_field || 'label'}
                          yField={widget.visualization.y_field || 'value'}
                          unit={widget.visualization.unit}
                          isHorizontal={widget.visualization.chart_type === 'horizontal_bar'}
                          description={widget.explanation}
                        />
                      );
                    }

                    if (widget.visualization?.chart_type === 'line') {
                      return (
                        <LineChartCard
                          key={widget.widget_id}
                          title={widget.title}
                          data={widget.result.rows}
                          xField={widget.visualization.x_field || 'academic_year'}
                          yField={widget.visualization.y_field || 'value'}
                          unit={widget.visualization.unit}
                          description={widget.explanation}
                        />
                      );
                    }

                    // Fallback to table
                    return (
                      <Card key={widget.widget_id} style={{ padding: 'var(--spacing-md)' }}>
                        <h4 style={{ margin: '0 0 12px 0', fontSize: '15px' }}>{widget.title}</h4>
                        <ResultTableView result={widget.result} />
                      </Card>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Section C: Deterministic Anomaly Alerts Section */}
          {dashboard.widgets.some((w) => w.anomaly && w.anomaly.detected) && (
            <div>
              <h3
                style={{
                  fontSize: 'var(--font-size-md)',
                  fontWeight: 700,
                  color: '#92400E',
                  margin: '0 0 12px 0',
                }}
              >
                Statistical Anomaly Insights
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                {dashboard.widgets
                  .filter((w) => w.anomaly && w.anomaly.detected)
                  .map((widget) => (
                    <AnomalyInsightCard key={widget.widget_id} anomaly={widget.anomaly} />
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. Schedules Modal Drawer */}
      {showScheduleModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
        >
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-lg)',
              maxWidth: '560px',
              width: '100%',
              padding: 'var(--spacing-lg)',
              maxHeight: '90vh',
              overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Calendar size={20} color="#1E3A8A" />
                <h3 style={{ margin: 0, fontSize: '18px', color: '#0F172A' }}>Scheduled Refresh Manager</h3>
              </div>
              <button
                onClick={() => setShowScheduleModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B' }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#475569' }}>
              Configure automatic background refresh intervals for your authorized dashboards. Minimum interval is 60 minutes.
            </p>

            {scheduleMessage && (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  borderRadius: '4px',
                  color: '#1E40AF',
                  fontSize: '13px',
                  marginBottom: '16px',
                }}
              >
                {scheduleMessage}
              </div>
            )}

            {/* Create Schedule Section */}
            <div
              style={{
                backgroundColor: '#F8FAFC',
                padding: '14px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                marginBottom: '20px',
              }}
            >
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B', marginBottom: '8px' }}>
                Schedule Current Dashboard ({dashboard?.title})
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <select
                  value={scheduleInterval}
                  onChange={(e) => setScheduleInterval(Number(e.target.value))}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '4px',
                    border: '1px solid #CBD5E1',
                    fontSize: '13px',
                    flex: 1,
                  }}
                >
                  <option value={60}>Every 1 Hour (60 mins)</option>
                  <option value={120}>Every 2 Hours (120 mins)</option>
                  <option value={360}>Every 6 Hours (360 mins)</option>
                  <option value={720}>Every 12 Hours (720 mins)</option>
                  <option value={1440}>Daily (24 Hours / 1440 mins)</option>
                </select>

                <button
                  onClick={handleCreateSchedule}
                  disabled={scheduleSubmitting}
                  style={{
                    backgroundColor: '#1E3A8A',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '7px 14px',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: scheduleSubmitting ? 'not-allowed' : 'pointer',
                  }}
                >
                  {scheduleSubmitting ? 'Saving...' : 'Set Schedule'}
                </button>
              </div>
            </div>

            {/* Existing Schedules */}
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A', marginBottom: '8px' }}>
              Active Schedules ({schedules.length})
            </div>
            {schedules.length === 0 ? (
              <div style={{ fontSize: '13px', color: '#64748B', fontStyle: 'italic' }}>
                No active schedules configured for your account.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {schedules.map((s) => (
                  <div
                    key={s.schedule_id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '10px 12px',
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      borderRadius: '4px',
                      fontSize: '13px',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: '#1E293B' }}>{s.dashboard_title}</div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>
                        Every {s.interval_minutes} mins | Next:{' '}
                        {s.next_run_at ? new Date(s.next_run_at).toLocaleTimeString() : 'Pending'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleCancelSchedule(s.schedule_id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#EF4444',
                        padding: '4px',
                      }}
                      title="Cancel Schedule"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
