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

// In-memory cache for current user (to prevent flashing stale data after logout)
let cachedUser: User | null = null;

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
  // Return cached user if available
  if (cachedUser) {
    return cachedUser;
  }

  const response = await api("/auth/me");

  if (!response.ok) {
    throw new Error("Not authenticated");
  }

  const user = await response.json();
  cachedUser = user; // Cache the user
  return user;
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
 * Check authentication status
 */
export async function getAuthStatus(): Promise<AuthStatusResponse> {
  const response = await api("/auth/status");

  if (!response.ok) {
    return { authenticated: false };
  }

  return response.json();
}
