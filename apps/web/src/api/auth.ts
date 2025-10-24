/**
 * Authentication API functions
 */

import { api } from './fetcher';
import { API_BASE } from '@/lib/apiBase';

export interface User {
  id: string;
  email: string;
  name?: string;
  picture_url?: string;
  is_demo: boolean;
}

export interface SessionResponse {
  ok: boolean;
  user?: User;
}

export interface AuthStatusResponse {
  authenticated: boolean;
  user?: User;
}

/**
 * Start a demo session
 */
export async function startDemo(): Promise<SessionResponse> {
  const response = await api("/auth/demo/start", {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to start demo session");
  }

  return response.json();
}

/**
 * Redirect to Google OAuth login
 */
export function loginWithGoogle(): void {
  window.location.href = `${API_BASE}/auth/google/login`;
}

/**
 * Logout current user
 */
export async function logout(): Promise<void> {
  await api("/auth/logout", {
    method: "POST",
  });
}

/**
 * Get current user info
 */
export async function getCurrentUser(): Promise<User> {
  const response = await api("/auth/me");

  if (!response.ok) {
    throw new Error("Not authenticated");
  }

  return response.json();
}

/**
 * Check authentication status
 */
export async function getAuthStatus(): Promise<AuthStatusResponse> {
  const response = await api("/auth/status");

  if (!response.ok) {
    return { authenticated: false };
  }

  return response.json();
}
