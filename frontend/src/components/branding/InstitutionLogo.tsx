import React, { useState } from 'react';
import { Landmark } from 'lucide-react';
import styles from './InstitutionLogo.module.css';

export interface InstitutionLogoProps {
  departmentName?: string;
  className?: string;
}

export const InstitutionLogo: React.FC<InstitutionLogoProps> = ({
  departmentName = 'Department of Computer Science & Engineering',
  className = '',
}) => {
  const [imgError, setImgError] = useState(false);

  return (
    <div className={[styles.container, className].filter(Boolean).join(' ')}>
      <div className={styles.logoWrapper}>
        {!imgError ? (
          <img
            src="/assets/branding/vignanuniversity.png"
            alt="Vignan's Foundation for Science, Technology and Research (Deemed to be University)"
            className={styles.logoImg}
            onError={() => setImgError(true)}
          />
        ) : (
          <div className={styles.fallbackLogo} title="Vignan University Logo">
            <Landmark size={20} color="var(--color-brand-primary)" />
            <span className={styles.fallbackText}>VIGNAN UNIVERSITY</span>
          </div>
        )}
      </div>

      {departmentName && (
        <div className={styles.deptInfo}>
          <span className={styles.deptText}>{departmentName}</span>
        </div>
      )}
    </div>
  );
};
