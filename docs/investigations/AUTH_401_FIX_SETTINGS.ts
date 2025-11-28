// Fix for Settings page stuck on "Loading..." when not authenticated
//
// The issue: When session cookie is missing, fetchAndCacheCurrentUser() returns null,
// but the UI stays stuck showing "Loading..." instead of redirecting to login.
//
// Root cause: No session cookie (applylens_session) exists - user is not actually logged in.
// The CSRF token cookie exists, but that's not enough for authentication.
//
// This patch adds:
// 1. Timeout detection - if loading takes > 5 seconds, assume auth failed
// 2. Explicit redirect to /welcome when no user can be fetched
// 3. Better error state instead of infinite "Loading..."

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCurrentUser, fetchAndCacheCurrentUser } from '@/api/auth'

// In Settings.tsx, replace the useEffect that loads user email with:

useEffect(() => {
  let mounted = true
  let timeoutId: NodeJS.Timeout | null = null

  const loadUser = async () => {
    // Try cached first (fast path)
    const cached = getCurrentUser()
    if (cached?.email) {
      if (mounted) setAccountEmail(cached.email)
      return
    }

    // Set timeout - if we don't get a response in 5 seconds, assume not authenticated
    timeoutId = setTimeout(() => {
      if (mounted) {
        console.warn('[Settings] User fetch timeout - redirecting to login')
        navigate('/welcome', { replace: true })
      }
    }, 5000)

    // Fallback: fetch from API and cache it
    try {
      const fresh = await fetchAndCacheCurrentUser()

      // Clear timeout since we got a response
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = null
      }

      if (!mounted) return

      if (fresh?.email) {
        setAccountEmail(fresh.email)
      } else {
        // fetchAndCacheCurrentUser returned null = not authenticated
        console.warn('[Settings] No user returned from API - redirecting to login')
        navigate('/welcome', { replace: true })
      }
    } catch (error) {
      if (timeoutId) clearTimeout(timeoutId)
      if (mounted) {
        console.error('[Settings] Failed to fetch user:', error)
        navigate('/welcome', { replace: true })
      }
    }
  }

  loadUser()

  return () => {
    mounted = false
    if (timeoutId) clearTimeout(timeoutId)
  }
}, [navigate])

// Alternative: Add a LoginGuard around the Settings route
// In App.tsx or wherever routes are defined:
/*
<Route
  path="/settings"
  element={
    <LoginGuard>
      <Settings />
    </LoginGuard>
  }
/>
*/
