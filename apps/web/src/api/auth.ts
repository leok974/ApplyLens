/**
 * Authentication API functions
 */

import { api } from './fetcher';
import { API_BASE, apiFetch } from '@/lib/apiBase';

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

// In-memory cache for current user (to prevent flashing stale data after logout)
let cachedUser: User | null = null;

/**
 * Get cached user (synchronous, no API call)
 * Returns null if user not yet fetched
 */
export function getCurrentUser(): User | null {
  return cachedUser;
}

/**
 * Clear cached user data
 * Call this before logout to prevent stale user info from being displayed
 */
export function clearCurrentUser(): void {
  cachedUser = null;
  // Clear any localStorage if we use it in the future
  // localStorage.removeItem('user');
}

/**
 * Get current user from /auth/me endpoint
 * Uses apiFetch to ensure proper routing through API base
 */
export async function getMe(): Promise<User | null> {
  try {
    const data = await apiFetch('/auth/me', { method: 'GET' });
    return data as User;
  } catch (error) {
    console.error('Failed to fetch /auth/me:', error);
    return null;
  }
}

/**
 * Fetch current user from API and cache the result
 * Use this in components that need to ensure user data is loaded
 */
export async function fetchAndCacheCurrentUser(): Promise<User | null> {
  // Return cached user if already available
  if (cachedUser?.email) {
    return cachedUser;
  }

  try {
    const data = await getMe();
    if (data) {
      cachedUser = data;
    }
    return cachedUser;
  } catch (error) {
    console.error("Failed to fetch current user:", error);
    return cachedUser;
  }
}

/**
 * Start a demo session
 * Uses apiFetch to ensure CSRF token is set before making the request
 */
export async function startDemo(): Promise<SessionResponse> {
  const data = await apiFetch('/auth/demo/start', {
    method: 'POST',
  });

  return { ok: true, user: data };
}

/**
 * Redirect to Google OAuth login
 */
export function loginWithGoogle(): void {
  window.location.href = `${API_BASE}/auth/google/login`;
}

/**
 * Logout current user
 * Uses apiFetch to ensure proper CSRF handling and soft navigation
 */
export async function logout(): Promise<void> {
  await apiFetch('/auth/logout', { method: 'POST' });
  // Clear cached user data
  clearCurrentUser();
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
