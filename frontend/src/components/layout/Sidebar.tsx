import React from 'react';
import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';
import { APP_PHASE } from '../../constants/phases';
import {
  LayoutDashboard,
  MessageSquare,
  BarChart2,
  Shield,
} from 'lucide-react';

export interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const primaryNav = [
    { label: 'Strategic Intelligence', path: '/', icon: <LayoutDashboard size={18} /> },
    { label: 'Ask Agent 63', path: '/agent', icon: <MessageSquare size={18} />, badge: 'Active' },
    { label: 'Standing Dashboards', path: '/dashboards', icon: <Shield size={18} />, badge: 'Active' },
    { label: 'Analytics Workspace', path: '/analytics', icon: <BarChart2 size={18} />, badge: 'Active' },
  ];

  return (
    <>
      {isOpen && <div className={styles.overlay} onClick={onClose} aria-hidden="true" />}
      <aside className={[styles.sidebar, isOpen ? styles.sidebarOpen : ''].filter(Boolean).join(' ')}>
        <div className={styles.navSection}>
          {/* Institutional Navigation */}
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
        </div>

        {/* Institutional Identity Footer */}
        <div className={styles.footer}>
          <div className={styles.footerBadge}>
            <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)' }}>
              Agent 63 Analytics
            </span>
            <span>Vignan Institute of Tech & Sci</span>
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
