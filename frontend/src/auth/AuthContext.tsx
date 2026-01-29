import { createContext, useReducer, useEffect, type ReactNode } from 'react';
import type { AuthState, AuthAction, User } from '../types/auth';

const initialState: AuthState = {
  user: null,
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN': {
      const { access_token, refresh_token, user } = action.payload;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      return {
        user,
        accessToken: access_token,
        refreshToken: refresh_token,
        isAuthenticated: true,
      };
    }
    case 'REFRESH': {
      localStorage.setItem('access_token', action.payload.access_token);
      return {
        ...state,
        accessToken: action.payload.access_token,
      };
    }
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'LOGOUT':
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      return {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
      };
    default:
      return state;
  }
}

interface AuthContextValue extends AuthState {
  dispatch: React.Dispatch<AuthAction>;
}

export const AuthContext = createContext<AuthContextValue>({
  ...initialState,
  dispatch: () => undefined,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Load user info on mount if we have a token
  useEffect(() => {
    if (state.isAuthenticated && !state.user) {
      import('../api/auth').then(({ getMe }) => {
        getMe()
          .then((user: User) => dispatch({ type: 'SET_USER', payload: user }))
          .catch(() => dispatch({ type: 'LOGOUT' }));
      });
    }
  }, [state.isAuthenticated, state.user]);

  return (
    <AuthContext.Provider value={{ ...state, dispatch }}>
      {children}
    </AuthContext.Provider>
  );
}
