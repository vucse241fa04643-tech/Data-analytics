import React from 'react';
import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';
import { LayoutDashboard, MessageSquare, BarChart2, Shield, Lock, FileText, CheckCircle2 } from 'lucide-react';

export interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const primaryNav = [
    { label: 'Overview', path: '/', icon: <LayoutDashboard size={18} /> },
    { label: 'Agent 63', path: '/agent', icon: <MessageSquare size={18} />, badge: 'Workspace' },
    { label: 'Analytics', path: '/analytics', icon: <BarChart2 size={18} /> },
  ];

  const futureNav = [
    { label: 'Role Dashboards', icon: <Shield size={18} />, phase: 'Phase 5' },
    { label: 'Reconciliation', icon: <CheckCircle2 size={18} />, phase: 'Phase 14' },
    { label: 'Audit Trail', icon: <FileText size={18} />, phase: 'Phase 13' },
    { label: 'RBAC Scopes', icon: <Lock size={18} />, phase: 'Phase 5' },
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

          <div style={{ margin: 'var(--spacing-lg) 0 var(--spacing-xs) 0' }}>
            <div className={styles.sectionTitle}>Planned Features</div>
            <div className={styles.navList}>
              {futureNav.map((item, idx) => (
                <div key={idx} className={[styles.navItem, styles.disabledItem].join(' ')} title={`${item.label} - ${item.phase}`}>
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
            <span>Deterministic Analytics Engine</span>
            <span style={{ color: 'var(--color-brand-primary)', fontSize: '10px' }}>
              Phase 3: Frontend Foundation
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
