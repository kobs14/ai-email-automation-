import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Mail,
  MessageSquare,
  AlertCircle,
  Calendar,
  Settings,
  X,
} from 'lucide-react';
import { useAuth } from '../../auth/useAuth';
import { useQuery } from '@tanstack/react-query';
import { getPendingResponses } from '../../api/responses';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
    isActive
      ? 'bg-blue-50 text-blue-700'
      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
  }`;

export function Sidebar({ open, onClose }: SidebarProps) {
  const { isAdmin } = useAuth();

  const { data: pendingData } = useQuery({
    queryKey: ['responses', 'pending-count'],
    queryFn: getPendingResponses,
    refetchInterval: 30000,
  });
  const pendingCount = pendingData?.items.length ?? 0;

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-white border-r border-gray-200 flex flex-col transform transition-transform duration-200 ease-in-out
          ${open ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0 lg:static lg:z-auto`}
        aria-label="Sidebar navigation"
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
          <span className="text-lg font-bold text-gray-900">EcoClean</span>
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-gray-500 hover:text-gray-700"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Main navigation">
          <NavLink to="/dashboard" className={navLinkClass} onClick={onClose}>
            <LayoutDashboard className="w-5 h-5" />
            Dashboard
          </NavLink>

          <NavLink to="/emails" className={navLinkClass} onClick={onClose}>
            <Mail className="w-5 h-5" />
            Emails
          </NavLink>

          <NavLink to="/responses" className={navLinkClass} onClick={onClose}>
            <MessageSquare className="w-5 h-5" />
            Responses
            {pendingCount > 0 && (
              <span
                className="ml-auto bg-yellow-100 text-yellow-800 text-xs font-semibold px-2 py-0.5 rounded-full"
                aria-label={`${pendingCount} pending drafts`}
              >
                {pendingCount}
              </span>
            )}
          </NavLink>

          <NavLink to="/responses/failed" className={navLinkClass} onClick={onClose}>
            <AlertCircle className="w-5 h-5" />
            Failed Sends
          </NavLink>

          <NavLink to="/calendar" className={navLinkClass} onClick={onClose}>
            <Calendar className="w-5 h-5" />
            Calendar
          </NavLink>

          {isAdmin && (
            <NavLink to="/config" className={navLinkClass} onClick={onClose}>
              <Settings className="w-5 h-5" />
              Configuration
            </NavLink>
          )}
        </nav>

        {/* User info */}
        <UserInfo />
      </aside>
    </>
  );
}

function UserInfo() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="p-4 border-t border-gray-200">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold text-sm">
          {user.username[0].toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{user.username}</p>
          <p className="text-xs text-gray-500 capitalize">{user.role}</p>
        </div>
      </div>
    </div>
  );
}
