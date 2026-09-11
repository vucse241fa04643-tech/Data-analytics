import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import {
  MessageSquare,
  Send,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';

export const AgentPage: React.FC = () => {
  const [inputValue, setInputValue] = useState('');

  const exampleQuestions = [
    {
      domain: 'Attendance',
      prompt: 'Compare average course attendance across academic departments for the current semester.',
    },
    {
      domain: 'Performance',
      prompt: 'Show the pass percentage trend for core computer science courses between 2024 and 2025.',
    },
    {
      domain: 'Placements',
      prompt: 'Display placement eligibility counts categorized by academic department and CGPA tier.',
    },
    {
      domain: 'Curriculum',
      prompt: 'List course offerings with faculty assignments in the Department of Computer Science.',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)', height: '100%' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-primary)' }}>
              Agent 63 Conversational Analytics
            </h1>
            <StatusBadge variant="info">UI Foundation</StatusBadge>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Natural-language institutional query interface. Grounded in the 21-domain schema registry.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusBadge variant="neutral">
            <ShieldCheck size={14} style={{ marginRight: '4px' }} />
            <span>AI Orchestration: Phase 6 Target</span>
          </StatusBadge>
        </div>
      </div>

      {/* Main Conversation Canvas */}
      <Card style={{ flex: 1, minHeight: '440px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--spacing-xl) 0' }}>
          <EmptyState
            icon={<MessageSquare size={32} />}
            title="Conversational Workspace Ready"
            description="The conversational pipeline will be integrated in Phase 6 (LLM Intent Orchestration) and Phase 7 (Safe SQL Builder). No live AI calls or SQL queries are executed in Phase 3."
            action={
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                <AlertCircle size={14} color="var(--color-brand-accent)" />
                <span>Zero arbitrary SQL execution & zero external LLM API traffic</span>
              </div>
            }
          />
        </div>

        {/* Example Query Chips (Static UI Demonstration) */}
        <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: 'var(--spacing-md)', marginTop: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
            <Sparkles size={14} color="var(--color-brand-primary)" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Example Institutional Queries (Illustrative Only)
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '8px' }}>
            {exampleQuestions.map((q, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--color-bg-workspace)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-text-secondary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  cursor: 'pointer',
                  transition: 'border-color var(--transition-fast)',
                }}
                onClick={() => setInputValue(q.prompt)}
                title="Click to populate input placeholder"
              >
                <span style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--color-brand-primary)', fontSize: '10px' }}>
                  [{q.domain}]
                </span>
                <span style={{ lineHeight: 1.4 }}>{q.prompt}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Input Area (Disabled / Controlled) */}
        <div style={{ marginTop: 'var(--spacing-md)', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask an analytical question (Pipeline active in Phase 6+)..."
              disabled
              style={{
                width: '100%',
                padding: '12px var(--spacing-md)',
                backgroundColor: 'var(--color-bg-subtle)',
                border: '1px solid var(--color-border-strong)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--color-text-muted)',
                fontSize: 'var(--font-size-sm)',
                cursor: 'not-allowed',
              }}
              aria-label="Agent question input"
            />
          </div>
          <Button
            variant="primary"
            disabled
            rightIcon={<Send size={16} />}
            title="Conversational execution connects in Phase 6"
          >
            Ask Agent 63
          </Button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px' }}>
          <HelpCircle size={12} color="var(--color-text-muted)" />
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
            Input is inactive during Phase 3 foundation. Live execution connects in Phase 6 after Semantic Layer and RBAC.
          </span>
        </div>
      </Card>
    </div>
  );
};
