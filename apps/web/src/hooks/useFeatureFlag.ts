/**
 * Enhanced Feature Flag Hook with Percentage Rollout
 *
 * Supports gradual feature rollout based on user ID hashing.
 * Features can be rolled out to 10% → 25% → 50% → 100% of users.
 */

import { useMemo } from 'react';

/**
 * Feature flag configuration with rollout support
 */
export interface FeatureFlagConfig {
  /** Feature identifier */
  name: string;
  /** Global enable/disable toggle */
  enabled: boolean;
  /** Rollout percentage (0-100). If undefined, all users get the feature when enabled=true */
  rolloutPercentage?: number;
}

/**
 * Hash a string to a deterministic number between 0-99
 * Uses simple hash algorithm for consistent bucketing
 *
 * @internal - Exported for testing
 */
export function hashToBucket(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  // Map to 0-99 range
  return Math.abs(hash) % 100;
}

/**
 * Check if a user is included in a percentage rollout
 *
 * @param userId - Unique user identifier
 * @param percentage - Rollout percentage (0-100)
 * @returns true if user is in the rollout bucket
 */
export function isUserInRollout(userId: string, percentage: number): boolean {
  if (percentage >= 100) return true;
  if (percentage <= 0) return false;

  const bucket = hashToBucket(userId);
  return bucket < percentage;
}

/**
 * Check if a feature is enabled for a specific user
 *
 * @param config - Feature flag configuration
 * @param userId - Unique user identifier (email, ID, etc.)
 * @returns true if feature should be shown to this user
 */
export function useFeatureFlag(config: FeatureFlagConfig, userId: string): boolean {
  return useMemo(() => {
    // Feature globally disabled
    if (!config.enabled) {
      return false;
    }

    // No rollout percentage means 100% rollout
    if (config.rolloutPercentage === undefined) {
      return true;
    }

    // Check if user is in rollout bucket
    return isUserInRollout(userId, config.rolloutPercentage);
  }, [config.enabled, config.rolloutPercentage, config.name, userId]);
}

/**
 * Pre-configured feature flags for Email Risk v3.1
 */
export const EMAIL_RISK_V31_FLAGS = {
  /**
   * Email Risk Banner - Shows suspicious email warnings
   * Gradual rollout: 10% → 25% → 50% → 100%
   */
  EmailRiskBanner: {
    name: 'EmailRiskBanner',
    enabled: import.meta.env.VITE_FEATURE_EMAIL_RISK_BANNER === '1',
    rolloutPercentage: parseInt(
      import.meta.env.VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT || '100',
      10
    ),
  } as FeatureFlagConfig,

  /**
   * Email Risk Details Panel - Detailed risk breakdown
   */
  EmailRiskDetails: {
    name: 'EmailRiskDetails',
    enabled: import.meta.env.VITE_FEATURE_EMAIL_RISK_DETAILS === '1',
    rolloutPercentage: parseInt(
      import.meta.env.VITE_FEATURE_EMAIL_RISK_DETAILS_ROLLOUT || '100',
      10
    ),
  } as FeatureFlagConfig,

  /**
   * Email Risk Advice API - Backend risk scoring
   */
  EmailRiskAdvice: {
    name: 'EmailRiskAdvice',
    enabled: import.meta.env.VITE_FEATURE_EMAIL_RISK_ADVICE === '1',
    rolloutPercentage: parseInt(
      import.meta.env.VITE_FEATURE_EMAIL_RISK_ADVICE_ROLLOUT || '100',
      10
    ),
  } as FeatureFlagConfig,
};

/**
 * Hook for Email Risk Banner feature
 *
 * Example usage:
 * ```tsx
 * const showRiskBanner = useEmailRiskBanner(user.email);
 * return showRiskBanner && <EmailRiskBanner email={email} />;
 * ```
 */
export function useEmailRiskBanner(userId: string): boolean {
  return useFeatureFlag(EMAIL_RISK_V31_FLAGS.EmailRiskBanner, userId);
}

/**
 * Hook for Email Risk Details feature
 */
export function useEmailRiskDetails(userId: string): boolean {
  return useFeatureFlag(EMAIL_RISK_V31_FLAGS.EmailRiskDetails, userId);
}

/**
 * Hook for Email Risk Advice API feature
 */
export function useEmailRiskAdvice(userId: string): boolean {
  return useFeatureFlag(EMAIL_RISK_V31_FLAGS.EmailRiskAdvice, userId);
}

/**
 * Get rollout status for monitoring/debugging
 *
 * @returns Object with feature names and their rollout percentages
 */
export function getEmailRiskRolloutStatus(): Record<string, { enabled: boolean; rollout: number }> {
  return {
    EmailRiskBanner: {
      enabled: EMAIL_RISK_V31_FLAGS.EmailRiskBanner.enabled,
      rollout: EMAIL_RISK_V31_FLAGS.EmailRiskBanner.rolloutPercentage ?? 100,
    },
    EmailRiskDetails: {
      enabled: EMAIL_RISK_V31_FLAGS.EmailRiskDetails.enabled,
      rollout: EMAIL_RISK_V31_FLAGS.EmailRiskDetails.rolloutPercentage ?? 100,
    },
    EmailRiskAdvice: {
      enabled: EMAIL_RISK_V31_FLAGS.EmailRiskAdvice.enabled,
      rollout: EMAIL_RISK_V31_FLAGS.EmailRiskAdvice.rolloutPercentage ?? 100,
    },
  };
}
