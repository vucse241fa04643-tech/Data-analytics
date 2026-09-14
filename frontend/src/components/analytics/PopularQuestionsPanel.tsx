import React, { useEffect, useState } from 'react';
import { Card } from '../ui/Card';
import { PopularQuestion } from '../../types';
import { apiService } from '../../services/api';
import { TrendingUp, ShieldCheck, RefreshCw, Layers } from 'lucide-react';

interface PopularQuestionsPanelProps {
  onSelectQuestion: (questionText: string) => void;
  disabled?: boolean;
}

export const PopularQuestionsPanel: React.FC<PopularQuestionsPanelProps> = ({
  onSelectQuestion,
  disabled = false,
}) => {
  const [popularQuestions, setPopularQuestions] = useState<PopularQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchPopular = async () => {
    setIsLoading(true);
    try {
      const results = await apiService.getPopularQuestions(12);
      // Deduplicate entries using metric/query identity while preserving aggregated privacy-safe behavior
      const seen = new Map<string, PopularQuestion>();
      for (const q of results) {
        const key = `${q.metric_id}|${q.dimension_signature || ''}|${q.query_type || ''}|${(q.label || '').trim().toLowerCase()}`;
        if (!seen.has(key)) {
          seen.set(key, { ...q });
        } else {
          const existing = seen.get(key)!;
          existing.count += q.count;
          if (q.last_seen && (!existing.last_seen || q.last_seen > existing.last_seen)) {
            existing.last_seen = q.last_seen;
          }
        }
      }
      setPopularQuestions(Array.from(seen.values()).slice(0, 6));
    } catch {
      setPopularQuestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPopular();
  }, []);

  if (popularQuestions.length === 0 && !isLoading) {
    return null;
  }

  return (
    <Card
      style={{
        marginBottom: 'var(--spacing-md)',
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-card)',
        padding: 'var(--spacing-md)',
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '10px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: 'var(--color-brand-primary)',
              }}
            >
              <TrendingUp size={16} />
              <span
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-primary)',
                }}
              >
                Popular Analytical Inquiries
              </span>
            </div>

            {/* Badges */}
            <span
              style={{
                fontSize: '11px',
                fontWeight: 'var(--font-weight-semibold)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--color-brand-light)',
                color: 'var(--color-brand-primary)',
                border: '1px solid var(--color-brand-border)',
                letterSpacing: '0.02em',
              }}
            >
              Aggregated
            </span>

            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                fontWeight: 'var(--font-weight-semibold)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--color-success-bg)',
                color: 'var(--color-success)',
                border: '1px solid var(--color-success-border)',
              }}
            >
              <ShieldCheck size={12} />
              <span>Privacy-Safe</span>
            </span>
          </div>

          <p
            style={{
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-muted)',
              margin: '4px 0 0 0',
            }}
          >
            Frequently analyzed institutional metrics within your role scope
          </p>
        </div>

        <button
          type="button"
          onClick={fetchPopular}
          disabled={isLoading || disabled}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '4px 8px',
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            backgroundColor: 'transparent',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-sm)',
            cursor: isLoading || disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Refresh popular inquiries"
          onMouseOver={(e) => {
            if (!isLoading && !disabled) {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-hover)';
              e.currentTarget.style.color = 'var(--color-text-primary)';
            }
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--color-text-muted)';
          }}
        >
          <RefreshCw size={12} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Grid of Recommendation Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: '10px',
        }}
      >
        {popularQuestions.map((q, idx) => {
          const displayText = q.label || q.metric_id;
          const queryPrompt = `Show ${displayText.toLowerCase()}${
            q.dimension_signature ? ` by ${q.dimension_signature.replace(/dim\./g, '').replace(/,/g, ' and ')}` : ''
          }`;

          return (
            <button
              key={`${q.metric_id}-${idx}`}
              type="button"
              disabled={disabled}
              onClick={() => onSelectQuestion(queryPrompt)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                padding: '10px 14px',
                backgroundColor: 'var(--color-bg-workspace)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                textAlign: 'left',
                cursor: disabled ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease',
                gap: '6px',
                opacity: disabled ? 0.6 : 1,
              }}
              onMouseOver={(e) => {
                if (!disabled) {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)';
                  e.currentTarget.style.borderColor = 'var(--color-brand-secondary)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)';
                }
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-workspace)';
                e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-primary)',
                  lineHeight: 1.4,
                  wordBreak: 'break-word',
                }}
              >
                {displayText}
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  color: 'var(--color-brand-secondary)',
                  fontWeight: 'var(--font-weight-medium)',
                }}
              >
                <Layers size={11} />
                <span>
                  {q.count} {q.count === 1 ? 'query' : 'queries'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
};
export default PopularQuestionsPanel;
