import React from 'react';
import styles from './AgentCore.module.css';

export type AgentCoreState = 'idle' | 'listening' | 'processing' | 'result_ready';

export interface AgentCoreProps {
  state?: AgentCoreState;
  size?: number;
  className?: string;
  onClick?: () => void;
  title?: string;
}

export const AgentCore: React.FC<AgentCoreProps> = ({
  state = 'idle',
  size = 76,
  className = '',
  onClick,
  title,
}) => {
  const stateClass = styles[state] || styles.idle;
  const statusLabel =
    state === 'processing'
      ? 'Agent 63 analyzing institutional queries...'
      : state === 'listening'
      ? 'Agent 63 ready for query'
      : state === 'result_ready'
      ? 'Strategic institutional intelligence verified'
      : 'Agent 63 Institutional Intelligence Core';

  return (
    <div
      className={`${styles.agentCoreContainer} ${stateClass} ${className}`.trim()}
      style={{ width: `${size}px`, height: `${size}px` }}
      onClick={onClick}
      role="img"
      aria-label={title || statusLabel}
      title={title || statusLabel}
    >
      <div className={styles.coreGlow} aria-hidden="true" />
      <div className={styles.outerRing} aria-hidden="true" />
      <div className={styles.midRing} aria-hidden="true" />
      <div className={styles.innerOrb}>
        <span className={styles.insignia}>63</span>
      </div>
    </div>
  );
};
