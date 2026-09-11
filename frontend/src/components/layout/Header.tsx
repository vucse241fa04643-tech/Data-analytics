import React from 'react';
import styles from './Header.module.css';
import { InstitutionLogo } from '../branding/InstitutionLogo';
import { AccreditationBadges } from '../branding/AccreditationBadges';
import { StatusBadge } from '../common/StatusBadge';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { Menu, User, ShieldCheck } from 'lucide-react';

export interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { connectionState } = useBackendHealth();

  const getStatusBadge = () => {
    switch (connectionState) {
      case 'connected':
        return <StatusBadge variant="success">Backend Ready</StatusBadge>;
      case 'degraded':
        return (
          <StatusBadge variant="warning" title="Backend operational; college DB connection unconfigured">
            Foundation Ready (DB Unconfigured)
          </StatusBadge>
        );
      case 'offline':
        return <StatusBadge variant="danger">Backend Offline</StatusBadge>;
      default:
        return <StatusBadge variant="neutral">Connecting...</StatusBadge>;
    }
  };

  return (
    <header className={styles.header}>
      {/* Left: Institution Branding & Separate Agent 63 Mark */}
      <div className={styles.leftSection}>
        <button
          className={styles.menuBtn}
          onClick={onToggleSidebar}
          aria-label="Toggle navigation sidebar"
        >
          <Menu size={20} />
        </button>

        {/* Primary Institutional Logo */}
        <InstitutionLogo />

        <div className={styles.divider} />

        {/* Distinct Agent 63 Product Mark */}
        <div className={styles.projectBadge} title="Agent 63 Institutional Analytics Project Mark">
          <img
            src="/assets/branding/agent-63-mark.svg"
            alt="Agent 63 Project Mark"
            className={styles.projectMarkImg}
            width={22}
            height={22}
          />
          <span className={styles.projectTitle}>AGENT 63</span>
        </div>
      </div>

      {/* Center: System Telemetry Status */}
      <div className={styles.centerSection}>
        {getStatusBadge()}
      </div>

      {/* Right: Accreditations & User Profile Placeholder */}
      <div className={styles.rightSection}>
        <div className={styles.accreditationsWrapper}>
          <AccreditationBadges />
        </div>
        <div className={styles.userPill} title="Institutional Session Placeholder">
          <User size={16} color="var(--color-brand-primary)" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className={styles.userName}>Institutional User</span>
            <span className={styles.userRole}>Phase 5 Auth Target</span>
          </div>
          <ShieldCheck size={14} color="var(--color-brand-secondary)" />
        </div>
      </div>
    </header>
  );
};
