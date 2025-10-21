/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_USE_WAREHOUSE?: string
  readonly VITE_DEMO_MODE?: string
  readonly VITE_FEATURE_SUMMARIZE?: string
  readonly VITE_FEATURE_RISK_BADGE?: string
  readonly VITE_FEATURE_RAG_SEARCH?: string
  // Email Risk v3.1 feature flags
  readonly VITE_FEATURE_EMAIL_RISK_BANNER?: string
  readonly VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT?: string
  readonly VITE_FEATURE_EMAIL_RISK_DETAILS?: string
  readonly VITE_FEATURE_EMAIL_RISK_DETAILS_ROLLOUT?: string
  readonly VITE_FEATURE_EMAIL_RISK_ADVICE?: string
  readonly VITE_FEATURE_EMAIL_RISK_ADVICE_ROLLOUT?: string
  readonly DEV: boolean
  readonly PROD: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
