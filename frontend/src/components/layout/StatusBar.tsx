import React from 'react';
import styles from './StatusBar.module.css';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { Database, ShieldCheck, Cpu } from 'lucide-react';

export const StatusBar: React.FC = () => {
  const { connectionState, readinessData } = useBackendHealth();

  const getStatusText = () => {
    switch (connectionState) {
      case 'connected':
        return 'System Operational';
      case 'degraded':
        return 'Backend Ready (DB Unconfigured)';
      case 'offline':
        return 'Backend Offline';
      default:
        return 'Checking Health...';
    }
  };

  const getDotClass = () => {
    switch (connectionState) {
      case 'connected':
        return styles.ready;
      case 'degraded':
        return styles.degraded;
      case 'offline':
        return styles.offline;
      default:
        return styles.degraded;
    }
  };

  return (
    <footer className={styles.statusBar} role="contentinfo" aria-label="System status bar">
      <div className={styles.leftGroup}>
        <div className={styles.item}>
          <span className={[styles.statusDot, getDotClass()].join(' ')} />
          <span style={{ fontWeight: 'var(--font-weight-medium)' }}>{getStatusText()}</span>
        </div>
        <span className={styles.separator}>|</span>
        <div className={styles.item} title="Read-only PostgreSQL execution constraint">
          <Database size={13} />
          <span>
            College PostgreSQL:{' '}
            {readinessData?.dependencies.college_database === 'configured' ? 'Configured' : 'Unconfigured'}
          </span>
        </div>
        <span className={styles.separator}>|</span>
        <div className={styles.item} title="Authoritative Phase 1 Schema Registry">
          <Cpu size={13} />
          <span>
            Schema Registry:{' '}
            {readinessData?.dependencies.schema_registry_objects
              ? `${readinessData.dependencies.schema_registry_objects} Objects Verified`
              : 'Phase 1 Registry Available'}
          </span>
        </div>
      </div>

      <div className={styles.rightGroup}>
        <div className={styles.item}>
          <ShieldCheck size={13} color="var(--color-brand-primary)" />
          <span>Read-Only Execution Boundary Enforced</span>
        </div>
        <span className={styles.separator}>|</span>
        <div className={styles.item}>
          <span>No Synthetic Records</span>
        </div>
      </div>
    </footer>
  );
};
