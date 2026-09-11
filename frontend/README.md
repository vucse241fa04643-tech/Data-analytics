# Agent 63 – Institutional Analytics Frontend (Phase 3)

React and Vite frontend application for **Agent 63 – Secure Institutional Data Analytics Agent**.

> [!IMPORTANT]
> **Phase 3 Boundary Constraints:**
> - Zero fabricated institutional data: No fake student records, marks, attendance percentages, or synthetic charts.
> - Zero direct database connection: The frontend never connects directly to PostgreSQL or constructs arbitrary SQL.
> - Zero AI/LLM integration: Conversational execution connects in Phase 6.
> - Zero authentication/RBAC enforcement: Session indicators are structural placeholders for Phase 5.

---

## 1. Architectural Overview

The frontend is constructed using a high-trust, academic visual design language adhering to [`docs/ui-design.md`](../docs/ui-design.md).

```text
frontend/
├── public/
│   └── assets/branding/       # Official institutional logos and SVG project marks
├── src/
│   ├── app/                   # App shell, root routing, and providers
│   ├── components/
│   │   ├── branding/          # InstitutionLogo & AccreditationBadges placeholders
│   │   ├── common/            # StatusBadge, EmptyState, SectionHeader
│   │   ├── layout/            # Header, Sidebar, StatusBar, AppShell
│   │   └── ui/                # Card, Button, Input, Metric/Chart/Table Placeholders
│   ├── hooks/                 # Custom hooks (useBackendHealth)
│   ├── pages/                 # OverviewPage (/), AgentPage (/agent), AnalyticsPage (/analytics)
│   ├── services/              # API client abstraction (FastAPI backend health probe)
│   ├── styles/                # Centralized design tokens (tokens.css), reset, and global styles
│   ├── types/                 # TypeScript domain and telemetry interfaces
│   └── main.tsx               # Application entrypoint
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 2. Design Tokens & Visual Language

Styles are defined in [`src/styles/tokens.css`](src/styles/tokens.css) and exposed as CSS Custom Properties:
- **Atmospheric Background:** `--color-bg-workspace` (`#F4F7FB`)
- **Clean Surfaces:** `--color-bg-surface` (`#FFFFFF`), `--color-bg-subtle` (`#EDF2F7`)
- **Authoritative Navy Palette:** `--color-brand-primary` (`#1E3A8A`), `--color-brand-secondary` (`#2563EB`)
- **Deep Navy Typography:** `--color-text-primary` (`#0F172A`), `--color-text-secondary` (`#334155`)
- **Subtle Elevation & Hairline Borders:** `--shadow-card`, `--color-border-subtle` (`#E2E8F0`)

---

## 3. Route Structure

| Route | Page | Purpose | Current Phase 3 State |
|---|---|---|---|
| `/` | `OverviewPage` | Institutional overview & system telemetry | Live backend health reporting, architecture pillars |
| `/agent` | `AgentPage` | Conversational analytics workspace foundation | Structural layout, example prompt chips, inactive input |
| `/analytics` | `AnalyticsPage` | Institutional analytics workspace foundation | Inactive filter bar, KPI placeholders, chart/table containers |

---

## 4. Development Commands

### 4.1 Install Dependencies
```bash
npm.cmd install
# or
npm install
```

### 4.2 Start Local Development Server
```bash
npm.cmd run dev
# or
npm run dev
```
Development server runs at [http://localhost:5173](http://localhost:5173).

### 4.3 Build for Production
```bash
npm.cmd run build
# or
npm run build
```
Executes TypeScript typecheck (`tsc -b`) and Vite production bundle.

---

## 5. Environment Variables

Create `.env` in the `frontend/` directory (or use root `.env.example`):

```env
VITE_API_BASE_URL=http://localhost:8000
```

> [!CAUTION]
> All `VITE_*` environment variables are client-visible. Never put database credentials, API secrets, private keys, or tokens in frontend configuration.
