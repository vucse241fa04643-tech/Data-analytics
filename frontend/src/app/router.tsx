import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { OverviewPage } from '../pages/OverviewPage';
import { AgentPage } from '../pages/AgentPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { RoleDashboardPage } from '../pages/RoleDashboardPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <OverviewPage />,
      },
      {
        path: 'agent',
        element: <AgentPage />,
      },
      {
        path: 'analytics',
        element: <AnalyticsPage />,
      },
      {
        path: 'dashboards',
        element: <RoleDashboardPage />,
      },
    ],
  },
]);
