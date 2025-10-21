// Feature flags for ApplyLens frontend
// Controlled by environment variables (VITE_* prefix)

export const features = {
  // Existing features
  chatEnabled: true,
  policyStudioEnabled: true,
  
  // Warehouse metrics (BigQuery analytics)
  // Requires: USE_WAREHOUSE=1 on backend + VITE_USE_WAREHOUSE=1 on frontend
  warehouseMetrics: Boolean(import.meta.env.VITE_USE_WAREHOUSE),
  
  // SSE (Server-Sent Events) for real-time updates
  sseEnabled: true,
} as const;

// Type for feature flags
export type FeatureFlags = typeof features;

// Helper to check if a feature is enabled
export function isFeatureEnabled(feature: keyof FeatureFlags): boolean {
  return features[feature];
}
