import React from 'react';
import styles from './Card.module.css';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  interactive?: boolean;
  elevated?: boolean;
  className?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  interactive = false,
  elevated = false,
  className = '',
  ...props
}) => {
  const cardClasses = [
    styles.card,
    interactive ? styles.interactive : '',
    elevated ? styles.elevated : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={cardClasses} {...props}>
      {(title || subtitle || action) && (
        <div className={styles.cardHeader}>
          <div>
            {title && <div className={styles.title}>{title}</div>}
            {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={styles.cardBody}>{children}</div>
    </div>
  );
};
