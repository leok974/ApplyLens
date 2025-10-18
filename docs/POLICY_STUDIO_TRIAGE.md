# Policy Studio - Quick Triage Reference

**Status:** ✅ Complete  
**Date:** October 18, 2025

---

## ✅ Infrastructure Setup

### 1. TypeScript Configuration (`apps/web/tsconfig.json`)
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "*": ["src/*"]
    }
  }
}
```
**Status:** ✅ Already configured

### 2. Vite Configuration (`apps/web/vite.config.ts`)
```typescript
resolve: {
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
}
```
**Status:** ✅ Already configured

### 3. Routing (`apps/web/src/App.tsx`)
```tsx
import PolicyStudio from './pages/PolicyStudio'

<Route path="/policy-studio" element={<PolicyStudio />} />
```
**Status:** ✅ Already configured

### 4. Toast/Theme Providers
```tsx
import { ToastProvider } from './components/ui/use-toast'
import { Toaster } from './components/ui/sonner'

<ToastProvider>
  <div>
    <AppHeader />
    <main>
      <Routes>...</Routes>
    </main>
    <Toaster />
  </div>
</ToastProvider>
```
**Status:** ✅ Already configured

---

## ✅ Barrel Exports

### Policy Components (`apps/web/src/components/policy/index.ts`)
```typescript
export { PolicyBundleList } from "./PolicyBundleList";
export { PolicyBundleEditor } from "./PolicyBundleEditor";
export { RuleBuilder } from "./RuleBuilder";
export { RuleEditorDialog } from "./RuleEditorDialog";
export { LintPanel } from "./LintPanel";
export { SimulationPanel } from "./SimulationPanel";
export { ImportBundleDialog } from "./ImportBundleDialog";
```
**Status:** ✅ Created

**Usage:**
```typescript
import { PolicyBundleList, RuleBuilder } from "@/components/policy";
```

---

## ✅ API Client Structure (`apps/web/src/lib/policyClient.ts`)

### Exported Types
```typescript
export interface PolicyRule {
  id: string
  agent: string
  action: string
  effect: 'allow' | 'deny' | 'needs_approval'
  conditions?: Record<string, any>
  reason: string
  priority: number
  enabled: boolean
  budget?: { cost: number; compute: number; risk: 'low' | 'medium' | 'high' }
  tags?: string[]
  metadata?: Record<string, any>
}

export interface PolicyBundle {
  id: number
  version: string
  rules: PolicyRule[]
  notes?: string
  created_by: string
  created_at: string
  active: boolean
  canary_pct: number
  activated_at?: string
  activated_by?: string
  approval_id?: number
  source?: string
  source_signature?: string
  metadata?: Record<string, any>
}

export interface LintAnnotation {
  rule_id?: string
  severity: 'error' | 'warning' | 'info'
  message: string
  line?: number
  suggestion?: string
}

export interface LintResult {
  errors: LintAnnotation[]
  warnings: LintAnnotation[]
  info: LintAnnotation[]
  passed: boolean
  summary: {
    total_rules: number
    error_count: number
    warning_count: number
    info_count: number
    total_issues: number
  }
}

export interface SimResult {
  case_id: string
  matched_rule?: string
  effect: string
  reason: string
  budget?: any
}

export interface SimSummary {
  total_cases: number
  allow_count: number
  deny_count: number
  approval_count: number
  no_match_count: number
  allow_rate: number
  deny_rate: number
  approval_rate: number
  estimated_cost: number
  estimated_compute: number
  breaches: string[]
}

export interface SimResponse {
  summary: SimSummary
  results: SimResult[]
  examples: SimResult[]
}
```

### Exported Functions

#### Bundle Management
```typescript
export async function fetchBundles(params?: {
  limit?: number
  offset?: number
  active_only?: boolean
}): Promise<{ bundles: PolicyBundle[]; total: number }>

export async function fetchActiveBundle(): Promise<PolicyBundle | null>

export async function fetchBundle(id: number): Promise<PolicyBundle>

export async function createBundle(data: {
  version: string
  rules: PolicyRule[]
  notes?: string
  created_by: string
  metadata?: Record<string, any>
}): Promise<PolicyBundle>

export async function updateBundle(
  id: number,
  data: Partial<{
    rules: PolicyRule[]
    notes: string
    metadata: Record<string, any>
  }>
): Promise<PolicyBundle>

export async function deleteBundle(id: number): Promise<void>
```

#### Validation & Testing
```typescript
export async function lintRules(rules: PolicyRule[]): Promise<LintResult>

export async function simulateRules(params: {
  rules: PolicyRule[]
  dataset?: 'fixtures' | 'synthetic'
  synthetic_count?: number
  seed?: number
  custom_cases?: any[]
}): Promise<SimResponse>
```

#### Import/Export
```typescript
export async function exportBundle(id: number, expiryHours?: number): Promise<any>

export async function importBundle(
  signedBundle: any,
  importAsVersion?: string
): Promise<PolicyBundle>
```

#### Deployment & Rollback
```typescript
export async function activateBundle(
  id: number,
  approvalId: number,
  activatedBy: string,
  canaryPct: number = 10
): Promise<PolicyBundle>

export async function promoteCanary(
  id: number,
  targetPct: number
): Promise<PolicyBundle>

export async function rollbackBundle(
  id: number,
  reason: string,
  rolledBackBy: string,
  createIncident: boolean = true
): Promise<PolicyBundle>

export async function getCanaryStatus(id: number): Promise<any>
```

**Status:** ✅ Already implemented

---

## 📝 Component Export Patterns

### Components use **named exports**:
```typescript
// ✅ Correct pattern used in all policy components
export function PolicyBundleList({ ... }) {
  // component code
}

// ❌ Not using default exports
export default function PolicyBundleList({ ... }) {
  // ...
}
```

### Import patterns:
```typescript
// ✅ Via barrel export (recommended)
import { PolicyBundleList, RuleBuilder } from "@/components/policy";

// ✅ Direct import (also works)
import { PolicyBundleList } from "@/components/policy/PolicyBundleList";

// ❌ Won't work (no default exports)
import PolicyBundleList from "@/components/policy/PolicyBundleList";
```

---

## 🚀 Usage Example

```typescript
// pages/PolicyStudio.tsx
import { useState, useEffect } from 'react'
import { PolicyBundleList, PolicyBundleEditor, ImportBundleDialog } from '@/components/policy'
import { 
  fetchBundles, 
  fetchActiveBundle, 
  type PolicyBundle,
  type LintResult 
} from '@/lib/policyClient'

export default function PolicyStudio() {
  const [bundles, setBundles] = useState<PolicyBundle[]>([])
  const [activeBundle, setActiveBundle] = useState<PolicyBundle | null>(null)

  useEffect(() => {
    loadBundles()
  }, [])

  const loadBundles = async () => {
    const response = await fetchBundles({ limit: 20 })
    setBundles(response.bundles)
  }

  return (
    <div>
      <PolicyBundleList
        bundles={bundles}
        activeBundle={activeBundle}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
    </div>
  )
}
```

---

## 🔧 Common Troubleshooting

### TypeScript "Cannot find module" errors

**Causes:**
1. ❌ Wrong file casing vs import casing (Windows hides this)
2. ❌ Missing or incorrect export in component file
3. ❌ Stale TypeScript server cache

**Solutions:**
```bash
# 1. Check file name exactly matches import
# PolicyBundleList.tsx vs PolicyBundlelist.tsx

# 2. Verify component has named export
export function PolicyBundleList() { ... }  # ✅
export default PolicyBundleList            # ❌

# 3. Restart dev server and TS server
npm run dev  # Stop and restart
# In VSCode: Ctrl+Shift+P → "TypeScript: Restart TS Server"
```

### Import path errors

```typescript
// ✅ Use @ alias
import { PolicyBundleList } from "@/components/policy";

// ❌ Avoid relative paths from pages
import { PolicyBundleList } from "../components/policy/PolicyBundleList";

// ❌ Avoid deep imports
import PolicyBundleList from "@/components/policy/PolicyBundleList";
```

---

## ✅ Checklist

- [x] TypeScript paths configured (`@/*` → `src/*`)
- [x] Vite alias configured (`@` → `./src`)
- [x] React Router configured (`/policy-studio` route)
- [x] Toast providers configured (ToastProvider + Toaster)
- [x] Policy components barrel export created
- [x] API client with comprehensive types/functions
- [x] PolicyStudio page using barrel imports
- [x] All components use named exports (not default)

---

## 📊 Component Architecture

```
apps/web/src/
├── pages/
│   └── PolicyStudio.tsx           # Main page
├── components/
│   ├── policy/
│   │   ├── index.ts               # ✅ Barrel export
│   │   ├── PolicyBundleList.tsx
│   │   ├── PolicyBundleEditor.tsx
│   │   ├── RuleBuilder.tsx
│   │   ├── RuleEditorDialog.tsx
│   │   ├── LintPanel.tsx
│   │   ├── SimulationPanel.tsx
│   │   └── ImportBundleDialog.tsx
│   └── ui/                        # shadcn/ui components
└── lib/
    ├── policyClient.ts            # ✅ API client
    └── apiBase.ts                 # API base URL
```

---

## 🎯 Next Steps

All infrastructure is complete. You can now:

1. ✅ Import components using barrel exports
2. ✅ Use typed API client functions
3. ✅ Navigate to `/policy-studio`
4. ✅ Create/edit/test policy bundles
5. ✅ Lint and simulate policies

**No additional setup needed!** 🎉
