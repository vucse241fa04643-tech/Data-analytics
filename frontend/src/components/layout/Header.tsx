import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Header.module.css';
import { InstitutionLogo } from '../branding/InstitutionLogo';
import { AccreditationBadges } from '../branding/AccreditationBadges';
import { StatusBadge } from '../common/StatusBadge';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { useAuth } from '../../context/AuthContext';
import { APP_PHASE } from '../../constants/phases';
import { Menu, User, ShieldCheck, LogOut, KeyRound } from 'lucide-react';

export interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { connectionState } = useBackendHealth();
  const { user: userProfile, logout } = useAuth();
  const navigate = useNavigate();
  const [showProfileModal, setShowProfileModal] = useState(false);

  const handleLogout = async () => {
    await logout();
    setShowProfileModal(false);
    navigate('/login', { replace: true });
  };

  const getStatusBadge = () => {
    switch (connectionState) {
      case 'connected':
      case 'degraded':
        return (
          <StatusBadge
            variant="success"
            title={`${APP_PHASE.NAME} — Real-time execution, verification, and export active`}
          >
            {APP_PHASE.STATUS_LABEL}
          </StatusBadge>
        );
      case 'offline':
        return <StatusBadge variant="danger">Backend Offline</StatusBadge>;
      default:
        return <StatusBadge variant="neutral">Connecting...</StatusBadge>;
    }
  };

  return (
    <>
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

        {/* Right: Accreditations, User Profile, & Logout */}
        <div className={styles.rightSection}>
          <div className={styles.accreditationsWrapper}>
            <AccreditationBadges />
          </div>

          <button
            type="button"
            className={styles.userPill}
            onClick={() => setShowProfileModal(true)}
            title={userProfile ? `Institutional User: ${userProfile.username} (${userProfile.roles.join(', ')})` : 'Institutional Identity'}
            style={{ cursor: 'pointer', background: 'none', border: '1px solid var(--color-border-subtle)', textAlign: 'left' }}
            aria-label="Institutional User Profile and RBAC Status"
          >
            <User size={16} color="var(--color-brand-primary)" />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className={styles.userName}>
                {userProfile?.username || 'Institutional User'}
              </span>
              <span className={styles.userRole}>
                {userProfile?.roles?.length ? `${userProfile.roles.join(', ')} • RBAC Active` : 'Authenticated • RBAC Active'}
              </span>
            </div>
            <ShieldCheck size={14} color="var(--color-brand-secondary)" />
          </button>

          {/* Quick Sign Out Action */}
          <button
            type="button"
            className={styles.logoutBtn}
            onClick={handleLogout}
            title="Sign out of Agent 63 session"
            aria-label="Sign out of Agent 63 session"
          >
            <LogOut size={15} />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Institutional User Profile Modal */}
      {showProfileModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-modal-title"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(2px)',
          }}
          onClick={() => setShowProfileModal(false)}
        >
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-subtle)',
              boxShadow: 'var(--shadow-card)',
              width: '100%',
              maxWidth: '420px',
              padding: 'var(--spacing-xl)',
              margin: 'var(--spacing-md)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--spacing-md)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <KeyRound size={20} color="var(--color-brand-primary)" />
                <h3 id="profile-modal-title" style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                  Institutional Identity & Session
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowProfileModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: 'var(--color-text-muted)' }}
                aria-label="Close dialog"
              >
                &times;
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ padding: '12px', backgroundColor: 'var(--color-bg-workspace)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Authenticated Account</div>
                <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-brand-primary)', marginTop: '2px' }}>
                  {userProfile?.username || 'Authenticated Principal'}
                </div>
                {userProfile?.email && (
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                    {userProfile.email}
                  </div>
                )}
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginTop: '6px' }}>
                  <strong>Assigned Roles:</strong> {userProfile?.roles?.join(', ') || 'N/A'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--color-brand-secondary)', marginTop: '4px' }}>
                  RBAC Enforcement Boundary Active (Server-side Authorized)
                </div>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px',
                  backgroundColor: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-danger-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-danger)',
                  cursor: 'pointer',
                  fontWeight: 'var(--font-weight-medium)',
                  transition: 'all var(--transition-fast)',
                }}
              >
                <LogOut size={16} />
                Sign Out Session
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
export default Header;
