/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_USE_WAREHOUSE?: string
  readonly VITE_DEMO_MODE?: string
  readonly VITE_FEATURE_SUMMARIZE?: string
  readonly VITE_FEATURE_RISK_BADGE?: string
  readonly VITE_FEATURE_RAG_SEARCH?: string
  readonly DEV: boolean
  readonly PROD: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
