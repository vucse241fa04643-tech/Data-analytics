import React, { useState } from 'react';
import styles from './AccreditationBadges.module.css';

export interface AccreditationBadgesProps {
  className?: string;
}

export const AccreditationBadges: React.FC<AccreditationBadgesProps> = ({ className = '' }) => {
  const [naacError, setNaacError] = useState(false);
  const [nbaError, setNbaError] = useState(false);

  return (
    <div className={[styles.badgesContainer, className].filter(Boolean).join(' ')} aria-label="Official Institutional Accreditations">
      {/* NAAC A+ Accreditation */}
      <div className={styles.badgeCard} title="NAAC 'A+' Grade Accreditation">
        {!naacError ? (
          <img
            src="/assets/branding/naac-a+.png"
            alt="NAAC A+ Accredited Institution"
            className={styles.naacImg}
            onError={() => setNaacError(true)}
          />
        ) : (
          <span style={{ fontSize: '10px', fontWeight: 'bold', color: 'var(--color-brand-primary)' }}>
            NAAC A+
          </span>
        )}
      </div>

      {/* NBA Accreditation */}
      <div className={styles.badgeCard} title="National Board of Accreditation (NBA)">
        {!nbaError ? (
          <img
            src="/assets/branding/nba-logo.png"
            alt="NBA Accredited Programs"
            className={styles.nbaImg}
            onError={() => setNbaError(true)}
          />
        ) : (
          <span style={{ fontSize: '10px', fontWeight: 'bold', color: 'var(--color-brand-primary)' }}>
            NBA
          </span>
        )}
      </div>
    </div>
  );
};
