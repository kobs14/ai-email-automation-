import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/emails': 'Emails',
  '/responses': 'Responses',
  '/responses/failed': 'Failed Responses',
  '/calendar': 'Calendar',
  '/config': 'Configuration',
};

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Determine page title from path
  const pathBase = '/' + location.pathname.split('/').filter(Boolean).slice(0, 2).join('/');
  const title = pageTitles[location.pathname] || pageTitles[pathBase] || 'EcoClean';

  return (
    <div className="flex h-screen overflow-hidden">
      <a href="#main-content" className="skip-to-main">
        Skip to main content
      </a>

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header title={title} onMenuClick={() => setSidebarOpen(true)} />

        <main
          id="main-content"
          className="flex-1 overflow-y-auto p-4 lg:p-6"
          tabIndex={-1}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
