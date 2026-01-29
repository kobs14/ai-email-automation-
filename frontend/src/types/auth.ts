export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  last_login_at?: string;
  created_at?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
}

export type AuthAction =
  | { type: 'LOGIN'; payload: LoginResponse }
  | { type: 'REFRESH'; payload: { access_token: string } }
  | { type: 'LOGOUT' }
  | { type: 'SET_USER'; payload: User };
