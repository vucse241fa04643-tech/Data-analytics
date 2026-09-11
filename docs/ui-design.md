# Agent 63 – Institutional UI & UX Design System

> **Visual Source of Truth:** Institutional Reference Specification  
> **Philosophy:** High-trust, authoritative academic elegance. Not a ChatGPT clone, not a dark SaaS template, and not a generic cyberpunk dashboard.

---

## 1. Visual Language & Principles
The Agent 63 interface is crafted specifically for college leadership, department heads, and academic quality cells. The design reflects stability, clarity, and institutional prestige:
- **Clean Surfaces:** Crisp, pure white (`#FFFFFF`) cards and structural containers.
- **Atmospheric Background:** Calming, ultra-light tinted blue workspace background (`#F4F7FB` to `#EDF2F7`), creating depth without visual fatigue.
- **Institutional Blue Accents:** Refined navy and royal blue accents that denote authority and trustworthiness.
- **Deep Navy Typography:** High-contrast, dark slate/navy typography for crisp readability on high-resolution displays.
- **Subtle Borders & Elevation:** Hairline borders (`1px solid #E2E8F0`) with soft, diffused institutional drop shadows rather than heavy borders or harsh neon glows.
- **Restrained Visual Dynamics:** Purposeful micro-transitions; no distracting animations or gaudy gradient fills.

---

## 2. Centralized Design Tokens [IMPLEMENTED - Phase 3]

The styling architecture is governed by a centralized CSS variable design token system implemented in `frontend/src/styles/tokens.css`. Components consume tokens rather than hard-coded inline values.

```css
:root {
  /* Surface & Background Tokens */
  --color-bg-workspace: #F4F7FB;         /* Canvas background */
  --color-bg-surface: #FFFFFF;           /* Card & container surfaces */
  --color-bg-subtle: #EDF2F7;            /* Input backgrounds & inactive tabs */
  --color-bg-hover: #E2E8F0;             /* Interactive hover state */
  
  /* Institutional Brand Palette */
  --color-brand-primary: #1E3A8A;        /* Deep institutional blue */
  --color-brand-secondary: #2563EB;      /* Active state & link blue */
  --color-brand-accent: #3B82F6;         /* Highlight accent */
  --color-brand-light: #EFF6FF;          /* Highlight pill backgrounds */

  /* Typography Colors */
  --color-text-primary: #0F172A;         /* Slate dark navy for primary headers */
  --color-text-secondary: #334155;       /* Body text & labels */
  --color-text-muted: #64748B;           /* Captions, timestamps, and hints */
  --color-text-inverse: #FFFFFF;         /* Text on dark/brand backgrounds */

  /* Structural & Border Tokens */
  --color-border-subtle: #E2E8F0;        /* Card and panel borders */
  --color-border-strong: #CBD5E1;        /* Focused inputs & dividers */
  --color-border-accent: #93C5FD;        /* Focused brand borders */

  /* Semantic Feedback Tokens */
  --color-success: #059669;              /* Verified figures, upward trends */
  --color-success-bg: #ECFDF5;
  --color-warning: #D97706;              /* Approaching thresholds */
  --color-warning-bg: #FFFBEB;
  --color-danger: #DC2626;               /* Anomaly alerts, critical drops */
  --color-danger-bg: #FEF2F2;
  --color-info: #0284C7;                 /* Metric definitions & clarifications */
  --color-info-bg: #F0F9FF;

  /* Typography Stack */
  --font-family-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Spacing Scale */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-2xl: 48px;

  /* Shape & Elevation */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-pill: 9999px;
  --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-elevated: 0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -1px rgba(15, 23, 42, 0.04);
}
```

*Note: Exact brand hex codes will align with the official college identity guidelines when assets are formally attached.*

---

## 3. Planned Component Architecture

### 1. Institutional Header
- **Layout:** Full-width header spanning the top of the interface.
- **Left Region:** Official College Logo and Institution Wordmark.
- **Center Region:** Department Identity (e.g., "Department of Computer Science & Engineering") and **AGENT 63** core badge.
- **Right Region:** Accreditation badges (e.g., NAAC 'A++' Grade, NBA Accredited, Autonomous Status) and User Profile/Role indicator.

### 2. Institution Logo Area
- Dedicated container ensuring proper aspect ratio and contrast for official vector crests without distortion.

### 3. Department & Project Identity
- Crisp dual-line typography: Primary title (`AGENT 63`), Subtitle (`Institutional Data Intelligence`).

### 4. Accreditation & Recognition Logo Area
- Harmonized badge cluster honoring statutory accreditations.

### 5. Navigation Sidebar
- Collapsible vertical navigation bar:
  - Overview / Home
  - Conversational Analytics
  - Role Dashboards (Management, Principal, Dean, HOD, IQAC)
  - Anomaly Alerts
  - Query History & Audit
  - Official Report Reconciliation
  - Settings & RBAC Scopes

### 6. Analytics Workspace
- Primary central canvas hosting the conversational flow, query input, and interactive result displays.

### 7. Question Input Area
- Prominently placed, accessible search/input box with:
  - Clean placeholder text (*"Ask an analytical question about attendance, marks, enrollment..."*).
  - Quick query chips/suggestions (e.g., *"CSE 2025 Average Attendance"*, *"Pass Percentage Comparison 2024 vs 2025"*).
  - Submit button with distinct institutional blue styling.

### 8. Conversation Area
- Sequential transcript of analytical inquiries and responses, maintaining clean separation between user prompts and system result cards.

### 9. Institutional Result Card
- The core centerpiece of Agent 63. Designed as a structured, high-elevation card:
  - **Header:** Verified Answer / Primary Metric KPI (e.g., `82.6%`).
  - **Metric Sub-heading:** Metric Name and Formula.
  - **Scope Badges:** Academic Period, Department, Cohort Population.
  - **Active Filters:** Explicit filter conditions applied.
  - **Assumptions Panel:** Transparent notes on data handling (e.g., medical leaves excluded).
  - **Verification Stamp:** Badge indicating verification against official institutional criteria.

### 10. Metric Metadata Panel
- Contextual drawer or accordion detailing the mathematical definition, source tables, and institutional rationale.

### 11. Visualization Area
- Embedded directly within or beside the result card. Renders clean Recharts graphs (Line, Bar, KPI, Area) tailored to the dimensional query.

### 12. Insights & Highlights Panel
- Right-hand contextual rail displaying:
  - Key statistical highlights
  - Immediate anomalies or threshold warnings
  - Suggested follow-up inquiries (e.g., *"Compare with 2024"*, *"Break down by section"*)

### 13. Institutional Status Bar
- Bottom system bar displaying real-time system states:
  - `Ready` | `Analyzing Query` | `Query Validated` | `Fetching Data` | `Result Verified`
  - Active Data Scope indicator (e.g., `Scope: Department of Computer Science & Engineering`)
  - Latency indicator and read-only executor connection status.

### 14. User & Role Indicator
- Profile pill displaying authenticated user name, institutional designation, and active role scope.

### 15. Dashboard Cards
- Reusable KPI and chart widgets for role-based executive dashboards.

### 16. Alert & Anomaly Components
- Non-alarmist, clean callout cards (amber/red) displaying deviation metrics, baselines, and historical variance.

### 17. Data Tables
- Clean, paginated institutional tables with zebra striping, numeric right-alignment, and column sorting for detailed records.

### 18. Responsive Layouts
- **Desktop (Primary Target):** 3-column layout (Navigation, Analytics Workspace, Context Panel).
- **Laptop:** Fluid 2-column layout with toggleable context rail.
- **Tablet / Mobile:** Stacked layout with collapsible drawer navigation; chart containers maintain touch scrollability without layout breakage.
