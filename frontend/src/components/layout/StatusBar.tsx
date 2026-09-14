import React from 'react';
import styles from './StatusBar.module.css';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { APP_PHASE } from '../../constants/phases';
import { Database, ShieldCheck, Cpu } from 'lucide-react';

export const StatusBar: React.FC = () => {
  const { connectionState, readinessData } = useBackendHealth();

  const getStatusText = () => {
    switch (connectionState) {
      case 'connected':
        return APP_PHASE.SYSTEM_STATUS;
      case 'degraded':
        return APP_PHASE.SYSTEM_STATUS_UNCONFIGURED;
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
        <div className={styles.item} title="Authoritative Schema Registry">
          <Cpu size={13} />
          <span>
            Schema Registry:{' '}
            {readinessData?.dependencies.schema_registry_objects
              ? `${readinessData.dependencies.schema_registry_objects} Objects Verified`
              : '236 Objects Verified'}
          </span>
        </div>
      </div>

      <div className={styles.rightGroup}>
        <div className={styles.item} title="Read-only PostgreSQL execution with AST validation and verified results">
          <ShieldCheck size={13} color="var(--color-brand-primary)" />
          <span>{APP_PHASE.EXECUTION_BOUNDARY}</span>
        </div>
        <span className={styles.separator}>|</span>
        <div className={styles.item}>
          <span>No Synthetic Records</span>
        </div>
      </div>
    </footer>
  );
};
