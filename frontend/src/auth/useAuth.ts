import { useContext } from 'react';
import { AuthContext } from './AuthContext';

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  const hasRole = (...roles: string[]) => {
    return context.user ? roles.includes(context.user.role) : false;
  };

  const isAdmin = context.user?.role === 'admin';
  const isOperator = context.user?.role === 'operator' || isAdmin;

  return {
    ...context,
    hasRole,
    isAdmin,
    isOperator,
  };
}
