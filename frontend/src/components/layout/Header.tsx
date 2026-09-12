import React, { useEffect, useState } from 'react';
import styles from './Header.module.css';
import { InstitutionLogo } from '../branding/InstitutionLogo';
import { AccreditationBadges } from '../branding/AccreditationBadges';
import { StatusBadge } from '../common/StatusBadge';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { apiService } from '../../services/api';
import { UserProfileResponse } from '../../types';
import { Menu, User, ShieldCheck, LogOut, KeyRound } from 'lucide-react';

export interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { connectionState } = useBackendHealth();
  const [userProfile, setUserProfile] = useState<UserProfileResponse | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadUserProfile = async () => {
    try {
      const profile = await apiService.getCurrentUser();
      setUserProfile(profile);
    } catch {
      setUserProfile(null);
    }
  };

  useEffect(() => {
    loadUserProfile();

    const handleAuthChange = () => {
      loadUserProfile();
    };

    const handleOpenAuth = () => {
      setShowAuthModal(true);
    };

    window.addEventListener('agent63_auth_change', handleAuthChange);
    window.addEventListener('agent63_open_auth', handleOpenAuth);
    return () => {
      window.removeEventListener('agent63_auth_change', handleAuthChange);
      window.removeEventListener('agent63_open_auth', handleOpenAuth);
    };
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsSubmitting(true);
    try {
      await apiService.login(usernameInput, passwordInput);
      await loadUserProfile();
      window.dispatchEvent(new Event('agent63_auth_change'));
      setShowAuthModal(false);
      setUsernameInput('');
      setPasswordInput('');
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await apiService.logout();
    setUserProfile(null);
    window.dispatchEvent(new Event('agent63_auth_change'));
    setShowAuthModal(false);
  };

  const getStatusBadge = () => {
    switch (connectionState) {
      case 'connected':
      case 'degraded':
        return (
          <StatusBadge variant="success" title="Phase 6 Intent Engine active; database execution connects in Phase 7">
            Phase 6 • Intent Engine Ready
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

        {/* Right: Accreditations & User Profile */}
        <div className={styles.rightSection}>
          <div className={styles.accreditationsWrapper}>
            <AccreditationBadges />
          </div>

          <button
            type="button"
            className={styles.userPill}
            onClick={() => setShowAuthModal(true)}
            title={userProfile ? `Institutional User: ${userProfile.username}` : 'Manage Institutional Authentication'}
            style={{ cursor: 'pointer', background: 'none', border: '1px solid var(--color-border-subtle)', textAlign: 'left' }}
            aria-label="Institutional User Profile and RBAC Status"
          >
            <User size={16} color="var(--color-brand-primary)" />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className={styles.userName}>
                {userProfile?.username || 'Institutional User'}
              </span>
              <span className={styles.userRole}>
                {userProfile ? 'Authenticated • RBAC Active' : 'Authenticated • RBAC Active'}
              </span>
            </div>
            <ShieldCheck size={14} color="var(--color-brand-secondary)" />
          </button>
        </div>
      </header>

      {/* Institutional Authentication Dialog */}
      {showAuthModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="auth-modal-title"
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
          onClick={() => setShowAuthModal(false)}
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
                <h3 id="auth-modal-title" style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                  Institutional Authentication
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAuthModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: 'var(--color-text-muted)' }}
                aria-label="Close dialog"
              >
                &times;
              </button>
            </div>

            {userProfile ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ padding: '12px', backgroundColor: 'var(--color-bg-workspace)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)' }}>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Authenticated User</div>
                  <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-brand-primary)' }}>
                    {userProfile.username}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                    Roles: {userProfile.roles.join(', ')}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-brand-secondary)', marginTop: '4px' }}>
                    RBAC Enforcement Boundary Active (Phase 5)
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
                    border: '1px solid var(--color-border-strong)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-danger, #b91c1c)',
                    cursor: 'pointer',
                    fontWeight: 'var(--font-weight-medium)',
                  }}
                >
                  <LogOut size={16} />
                  Sign Out Session
                </button>
              </div>
            ) : (
              <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: 0 }}>
                  Enter your Vignan institutional credentials to authenticate your session and enable query intent analysis.
                </p>

                {authError && (
                  <div style={{ padding: '8px 12px', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-xs)', color: '#b91c1c' }}>
                    {authError}
                  </div>
                )}

                <div>
                  <label htmlFor="auth-username" style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', marginBottom: '4px', color: 'var(--color-text-primary)' }}>
                    Institutional Username
                  </label>
                  <input
                    id="auth-username"
                    type="text"
                    required
                    value={usernameInput}
                    onChange={(e) => setUsernameInput(e.target.value)}
                    placeholder="e.g. test_principal"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-border-strong)',
                      fontSize: 'var(--font-size-sm)',
                      backgroundColor: 'var(--color-bg-surface)',
                    }}
                  />
                </div>

                <div>
                  <label htmlFor="auth-password" style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', marginBottom: '4px', color: 'var(--color-text-primary)' }}>
                    Password
                  </label>
                  <input
                    id="auth-password"
                    type="password"
                    required
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    placeholder="••••••••"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-border-strong)',
                      fontSize: 'var(--font-size-sm)',
                      backgroundColor: 'var(--color-bg-surface)',
                    }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: 'var(--color-brand-primary)',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 'var(--font-weight-medium)',
                      cursor: isSubmitting ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {isSubmitting ? 'Authenticating...' : 'Sign In'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
};

