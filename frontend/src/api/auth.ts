import client from './client';
import type { LoginRequest, LoginResponse, User } from '../types/auth';

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await client.post<LoginResponse>('/auth/login', data);
  return response.data;
}

export async function refreshToken(refresh_token: string): Promise<{ access_token: string }> {
  const response = await client.post('/auth/refresh', { refresh_token });
  return response.data;
}

export async function logout(): Promise<void> {
  await client.post('/auth/logout');
}

export async function getMe(): Promise<User> {
  const response = await client.get<User>('/auth/me');
  return response.data;
}
