/**
 * Analytics and Telemetry Tracking
 *
 * Tracks user interactions for product insights.
 * In production, this would integrate with analytics providers like:
 * - Google Analytics
 * - Mixpanel
 * - Amplitude
 * - PostHog
 *
 * For now, we log to console in development and can easily swap in real providers.
 */

type AnalyticsEvent =
  | { name: 'bulk_action', action: 'archive' | 'mark_safe' | 'quarantine', count: number }
  | { name: 'bulk_action_undo', action: 'archive' | 'mark_safe' | 'quarantine', count: number }
  | { name: 'auto_advance_toggle', enabled: boolean }
  | { name: 'thread_viewer_navigation', direction: 'next' | 'prev' }
  | { name: 'summary_feedback', messageId: string, helpful: boolean };

/**
 * Track an analytics event.
 *
 * @param event - The event to track with its properties
 */
export function track(event: AnalyticsEvent): void {
  // In development, log to console
  if (import.meta.env.DEV) {
    console.log('[Analytics]', event.name, event);
  }

  // TODO: In production, integrate with real analytics provider
  // Example integrations:

  // Google Analytics
  // if (window.gtag) {
  //   window.gtag('event', event.name, event);
  // }

  // Mixpanel
  // if (window.mixpanel) {
  //   window.mixpanel.track(event.name, event);
  // }

  // PostHog
  // if (window.posthog) {
  //   window.posthog.capture(event.name, event);
  // }

  // Custom backend endpoint
  // fetch('/api/analytics', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ event: event.name, properties: event }),
  // }).catch(() => {
  //   // Fail silently - analytics should never break the app
  // });
}

/**
 * Track a page view.
 *
 * @param path - The page path
 */
export function trackPageView(path: string): void {
  if (import.meta.env.DEV) {
    console.log('[Analytics] Page View:', path);
  }

  // TODO: Integrate with analytics provider
}
