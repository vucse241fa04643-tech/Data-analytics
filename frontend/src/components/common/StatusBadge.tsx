import React from 'react';
import styles from './StatusBadge.module.css';

export interface StatusBadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  showDot?: boolean;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  variant = 'neutral',
  showDot = true,
  title,
  children,
  className = '',
}) => {
  return (
    <span
      className={[styles.badge, styles[variant], className].filter(Boolean).join(' ')}
      title={title}
    >
      {showDot && <span className={styles.dot} aria-hidden="true" />}
      <span>{children}</span>
    </span>
  );
};
