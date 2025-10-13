# shadcn/ui Layout Components - Complete Reference

## Overview

Complete set of production-ready layout components using shadcn/ui with dark theme integration. All components use `bg-card`, `bg-background`, and semantic color tokens—no white backgrounds.

## Installed Components (Latest Batch)

### New Components Added

- ✅ **Alert** - Info/warning/error messages
- ✅ **Table** - Data tables with sorting/filtering
- ✅ **Calendar** - Date picker calendar
- ✅ **Popover** - Floating content containers
- ✅ **Navigation Menu** - Horizontal navigation with dropdown support
- ✅ **Checkbox** - Form checkboxes
- ✅ **Radio Group** - Radio button groups

## Layout Components (Ready to Use)

### 1. AppHeader

**File:** `src/components/AppHeader.tsx`

Standardized header with navigation, actions, and theme toggle.

```tsx
import { AppHeader } from '@/components/AppHeader'

// In your app root
<AppHeader />
```

**Features:**

- Sticky positioning with backdrop blur
- Responsive navigation menu (hidden on mobile)
- Sync buttons on right
- Theme toggle integration
- Uses NavigationMenu component

**Customization:**

```tsx
// Modify nav links in AppHeader.tsx:
const navLinks = [
  ["Inbox", "/"],
  ["Search", "/search"],
  ["Tracker", "/tracker"],
  // Add more...
]
```

---

### 2. FilterBar

**File:** `src/components/FilterBar.tsx`

Reusable filter bar with inputs and select dropdown.

```tsx
import { FilterBar } from '@/components/FilterBar'

<FilterBar />
```

**Features:**

- Responsive flex layout
- Full-width on mobile, side-by-side on desktop
- Search inputs
- Label/category select dropdown
- Search button

**With State:**

```tsx
import { FilterBar } from '@/components/FilterBar'
import { useState } from 'react'

function SearchPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [domain, setDomain] = useState('')
  const [label, setLabel] = useState('any')

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <FilterBar 
        // Pass props for controlled inputs
      />
    </div>
  )
}
```

---

### 3. DryRunNotice (Alert-based)

**File:** `src/components/DryRunNotice.tsx`

Info panel using Alert component instead of pastel backgrounds.

```tsx
import { DryRunNotice } from '@/components/DryRunNotice'

<DryRunNotice />
```

**Custom Alerts:**

```tsx
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, CheckCircle } from "lucide-react"

// Success alert
<Alert className="border bg-card border-green-500/50">
  <CheckCircle className="h-4 w-4 text-green-500" />
  <AlertTitle>Success</AlertTitle>
  <AlertDescription>Emails synced successfully.</AlertDescription>
</Alert>

// Warning alert
<Alert className="border bg-card border-yellow-500/50">
  <AlertCircle className="h-4 w-4 text-yellow-500" />
  <AlertTitle>Warning</AlertTitle>
  <AlertDescription>Some emails failed to sync.</AlertDescription>
</Alert>

// Error alert
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Failed to connect to Gmail API.</AlertDescription>
</Alert>
```

---

### 4. DatePicker

**File:** `src/components/DatePicker.tsx`

Date picker with calendar popover (no white backgrounds).

```tsx
import { DatePicker } from '@/components/DatePicker'
import { useState } from 'react'

function FilterPage() {
  const [fromDate, setFromDate] = useState<Date>()
  const [toDate, setToDate] = useState<Date>()

  return (
    <div className="flex gap-2">
      <DatePicker label="From" value={fromDate} onChange={setFromDate} />
      <DatePicker label="To" value={toDate} onChange={setToDate} />
    </div>
  )
}
```

**Features:**

- CalendarIcon from lucide-react
- Format with date-fns
- Controlled component (optional value/onChange)
- Popover aligns to start (left-aligned)

---

### 5. ResultsTable

**File:** `src/components/ResultsTable.tsx`

Data table for search results or actions log.

```tsx
import { ResultsTable } from '@/components/ResultsTable'

const results = [
  {
    id: "1",
    from: "recruiting@example.com",
    subject: "Interview Invitation",
    received: "2 hours ago",
    reason: "Interview invitation",
    labels: ["Interview", "Important"]
  },
  // More results...
]

<ResultsTable 
  results={results}
  onViewDetails={(id) => console.log('View:', id)}
/>
```

**Features:**

- Responsive table with rounded borders
- Header with subtle background (`bg-background/40`)
- Row hover effect (`hover:bg-secondary/50`)
- Badge integration for labels
- Empty state message
- Action button column

**Customization:**

```tsx
// Add more columns in ResultsTable.tsx
<TableHead>Priority</TableHead>

// In TableBody:
<TableCell>{result.priority}</TableCell>
```

---

## Usage Patterns

### Complete Page Example

```tsx
import { AppHeader } from '@/components/AppHeader'
import { FilterBar } from '@/components/FilterBar'
import { DryRunNotice } from '@/components/DryRunNotice'
import { ResultsTable } from '@/components/ResultsTable'
import { pageShell, listStack } from '@/lib/layout'

export function SearchPage() {
  return (
    <>
      <AppHeader />
      <main className={pageShell}>
        <DryRunNotice />
        
        <section className="mt-4">
          <FilterBar />
        </section>

        <section className={listStack}>
          <ResultsTable results={searchResults} />
        </section>
      </main>
    </>
  )
}
```

---

### Date Range Filter

```tsx
import { DatePicker } from '@/components/DatePicker'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

function DateRangeFilter() {
  const [from, setFrom] = useState<Date>()
  const [to, setTo] = useState<Date>()

  const handleApply = () => {
    if (from && to) {
      // Apply date filter
      console.log('Filter from', from, 'to', to)
    }
  }

  return (
    <div className="rounded-xl border bg-card p-4 shadow-card">
      <div className="flex flex-wrap items-center gap-2">
        <DatePicker label="From" value={from} onChange={setFrom} />
        <DatePicker label="To" value={to} onChange={setTo} />
        <Button onClick={handleApply} className="ml-auto">
          Apply Filter
        </Button>
      </div>
    </div>
  )
}
```

---

### Table with Actions Menu

```tsx
import { ResultsTable } from '@/components/ResultsTable'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { MoreHorizontal } from 'lucide-react'

// In ResultsTable.tsx, replace the View button with:
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="sm">
      <MoreHorizontal className="h-4 w-4" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem onClick={() => onView(result.id)}>
      View Details
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => onArchive(result.id)}>
      Archive
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => onMarkSafe(result.id)}>
      Mark Safe
    </DropdownMenuItem>
    <DropdownMenuItem 
      className="text-destructive" 
      onClick={() => onDelete(result.id)}
    >
      Delete
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

## Migration Strategy

### Replace Existing Components

#### Old Nav (Custom Classes)

```tsx
// Before
<nav className="ml-4 hidden gap-2 md:flex">
  <a className="nav-link">Inbox</a>
  <a className="nav-link">Search</a>
</nav>
```

```tsx
// After
<AppHeader />
```

#### Old Filter Bar

```tsx
// Before
<div className="rounded-xl2 border border-[var(--border)] bg-[var(--elev1)] p-4">
  <input className="..." placeholder="Search..." />
  {/* More inputs */}
</div>
```

```tsx
// After
<FilterBar />
```

#### Old Info Blocks

```tsx
// Before
<div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
  <h4 className="font-semibold">Info</h4>
  <p className="text-gray-600">Message here</p>
</div>
```

```tsx
// After
<Alert className="border bg-card">
  <Info className="h-4 w-4" />
  <AlertTitle>Info</AlertTitle>
  <AlertDescription>Message here</AlertDescription>
</Alert>
```

#### Old Tables

```tsx
// Before
<table className="w-full">
  <thead className="bg-gray-50">
    <tr>...</tr>
  </thead>
  <tbody>...</tbody>
</table>
```

```tsx
// After
<ResultsTable results={data} />
```

---

## Color Token Reference

All components use these semantic tokens (mapped to your dark palette):

```css
--background: #10141b  (surface)
--foreground: #e7ebf3  (text)
--card: #141821        (elev1)
--primary: #2b66ff     (accent)
--secondary: #171c26   (elev2)
--muted: #171c26
--muted-foreground: #aeb8c7  (subtext)
--border: #242b39
--input: #0f131b
--ring: #7aa2ff        (focus ring)
```

### Usage in Components

```tsx
// Background
className="bg-background"  // Page background
className="bg-card"        // Card/panel background
className="bg-secondary"   // Hover states

// Text
className="text-foreground"       // Primary text
className="text-muted-foreground" // Secondary text

// Borders
className="border"         // Standard border
className="border-border"  // Explicit border color

// Interactive
className="hover:bg-secondary/50"  // Subtle hover
className="focus-visible:ring-2 focus-visible:ring-ring"  // Focus ring
```

---

## Additional Components Available

### Checkbox & Radio Group

```tsx
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'

// Checkbox
<div className="flex items-center gap-2">
  <Checkbox id="terms" />
  <Label htmlFor="terms">Accept terms and conditions</Label>
</div>

// Radio Group
<RadioGroup defaultValue="comfortable">
  <div className="flex items-center gap-2">
    <RadioGroupItem value="default" id="r1" />
    <Label htmlFor="r1">Default</Label>
  </div>
  <div className="flex items-center gap-2">
    <RadioGroupItem value="comfortable" id="r2" />
    <Label htmlFor="r2">Comfortable</Label>
  </div>
</RadioGroup>
```

### Popover (Generic)

```tsx
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'

<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline">Open</Button>
  </PopoverTrigger>
  <PopoverContent className="w-80">
    <div className="space-y-2">
      <h4 className="font-medium">Dimensions</h4>
      <p className="text-sm text-muted-foreground">
        Set the dimensions for the layer.
      </p>
    </div>
  </PopoverContent>
</Popover>
```

---

## Troubleshooting

### White Backgrounds Still Appearing?

1. **Check for inline styles:**

   ```tsx
   // Bad
   <div style={{ background: 'white' }}>
   
   // Good
   <div className="bg-card">
   ```

2. **Check for legacy Tailwind classes:**

   ```tsx
   // Bad
   className="bg-white bg-gray-50"
   
   // Good
   className="bg-card bg-background"
   ```

3. **Add to dark-hotfix.css if needed:**

   ```css
   /* Target specific library classes */
   html.dark .some-library-class {
     background: var(--elev-1) !important;
     color: var(--text) !important;
   }
   ```

### Components Not Styled Correctly?

1. **Check CSS import order in main.tsx:**

   ```tsx
   import './index.css'           // Tailwind + theme tokens (first)
   import './styles/theme.css'    // Legacy theme vars
   import './styles/dark-hotfix.css'  // Overrides (last)
   ```

2. **Verify theme is active:**

   ```tsx
   // Check in browser console
   document.documentElement.classList.contains('dark')  // Should be true
   ```

---

## Testing

All components work with E2E tests:

```typescript
// Playwright examples
await page.getByRole('navigation').getByText('Inbox').click()
await page.getByPlaceholder('Search subject/body…').fill('interview')
await page.getByRole('button', { name: 'Search' }).click()
await page.getByRole('table').getByText('recruiting@example.com').click()
```

---

## Summary

**Components Created:** 5 layout components + 7 new UI primitives  
**Files Modified:** 15 files  
**Status:** ✅ Ready for production use  
**Migration Path:** Gradual, page-by-page  
**Compatibility:** Works with existing dark-hotfix.css

**Next Steps:**

1. Replace Nav.tsx with AppHeader
2. Update Search page with FilterBar and ResultsTable
3. Replace info blocks with Alert components
4. Add DatePicker to filter interfaces
5. Gradually remove dark-hotfix.css overrides as components are migrated

---

**Commit:** `21a1d8c`  
**Branch:** `UI-polish`  
**All components use:** `bg-card`, `bg-background`, `bg-secondary` (no white backgrounds)
