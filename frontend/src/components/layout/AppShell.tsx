import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import styles from './AppShell.module.css';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className={styles.appLayout}>
      <Header onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />
      <div className={styles.bodyLayout}>
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className={styles.mainContent} id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
      <StatusBar />
    </div>
  );
};
