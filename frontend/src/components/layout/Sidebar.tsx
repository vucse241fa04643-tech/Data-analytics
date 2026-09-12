import React from 'react';
import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';
import { APP_PHASE } from '../../constants/phases';
import {
  LayoutDashboard,
  MessageSquare,
  BarChart2,
  Shield,
  Lock,
  FileText,
  CheckCircle2,
  ShieldAlert,
  Server,
} from 'lucide-react';

export interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const primaryNav = [
    { label: 'Overview', path: '/', icon: <LayoutDashboard size={18} /> },
    { label: 'Agent 63', path: '/agent', icon: <MessageSquare size={18} />, badge: 'Active' },
    { label: 'Role Dashboards', path: '/dashboards', icon: <Shield size={18} />, badge: 'Phase 12 Active' },
    { label: 'Analytics', path: '/analytics', icon: <BarChart2 size={18} />, badge: 'Active' },
  ];

  const activeCapabilities = [
    { label: 'Official Verification', icon: <CheckCircle2 size={18} />, phase: 'Phase 14 Active' },
    { label: 'Query Audit Log', icon: <FileText size={18} />, phase: 'Phase 13 Active' },
    { label: 'RBAC Scopes', icon: <Lock size={18} />, phase: 'Phase 5 Active' },
  ];

  const futureNav = [
    { label: 'Adversarial Security', icon: <ShieldAlert size={18} />, phase: 'Phase 15' },
    { label: 'Production Staging', icon: <Server size={18} />, phase: 'Phase 16' },
  ];

  return (
    <>
      {isOpen && <div className={styles.overlay} onClick={onClose} aria-hidden="true" />}
      <aside className={[styles.sidebar, isOpen ? styles.sidebarOpen : ''].filter(Boolean).join(' ')}>
        <div className={styles.navSection}>
          <div className={styles.sectionTitle}>Institutional Analytics</div>
          <nav className={styles.navList}>
            {primaryNav.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  [styles.navItem, isActive ? styles.navItemActive : ''].filter(Boolean).join(' ')
                }
                onClick={() => {
                  if (window.innerWidth <= 768) onClose();
                }}
                end={item.path === '/'}
              >
                <span className={styles.navIcon}>{item.icon}</span>
                <span>{item.label}</span>
                {item.badge && <span className={styles.badge}>{item.badge}</span>}
              </NavLink>
            ))}
          </nav>

          {/* Integrated Active Capabilities */}
          <div style={{ margin: 'var(--spacing-md) 0 var(--spacing-xs) 0' }}>
            <div className={styles.sectionTitle}>Active Subsystems</div>
            <div className={styles.navList}>
              {activeCapabilities.map((item, idx) => (
                <div
                  key={idx}
                  className={[styles.navItem, styles.disabledItem].join(' ')}
                  title={`${item.label} — ${item.phase} (Integrated into Agent & Dashboards)`}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <span>{item.label}</span>
                  <span
                    className={styles.badge}
                    style={{
                      backgroundColor: 'var(--color-success-bg)',
                      color: 'var(--color-success)',
                      border: '1px solid var(--color-success-border)',
                    }}
                  >
                    {item.phase}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Planned Future Phases */}
          <div style={{ margin: 'var(--spacing-md) 0 var(--spacing-xs) 0' }}>
            <div className={styles.sectionTitle}>Planned Phases</div>
            <div className={styles.navList}>
              {futureNav.map((item, idx) => (
                <div
                  key={idx}
                  className={[styles.navItem, styles.disabledItem].join(' ')}
                  title={`${item.label} — ${item.phase}`}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <span>{item.label}</span>
                  <span className={styles.badge}>{item.phase}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <div className={styles.footerBadge}>
            <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)' }}>
              Agent 63 Architecture
            </span>
            <span>Secure Institutional Analytics</span>
            <span style={{ color: 'var(--color-brand-primary)', fontSize: '10px', fontWeight: 'var(--font-weight-semibold)' }}>
              {APP_PHASE.FOOTER_PHASE}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
export default Sidebar;
