/**
 * Common layout class helpers for consistent spacing and structure
 * Use these to maintain uniform appearance across all pages
 */

/** Main page container with max-width and padding */
export const pageShell = 'mx-auto max-w-6xl px-4 py-6'

/** Stack of items with vertical spacing (for lists, cards, etc.) */
export const listStack = 'mt-4 grid gap-3'

/** Standard panel/card container with shadow */
export const panel = 'rounded-xl border bg-card p-4 shadow-card'

/** Filter bar with responsive flex layout */
export const filterBar = 'rounded-xl border bg-card p-4 shadow-card flex flex-wrap items-center gap-2'

/** Header container with sticky positioning */
export const headerContainer = 'sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60'

/** Header inner content wrapper */
export const headerInner = 'mx-auto flex max-w-6xl items-center gap-3 px-4 py-3'

/** Navigation links group */
export const navGroup = 'ml-4 hidden gap-2 md:flex'

/** Header actions group (right side) */
export const headerActions = 'ml-auto flex items-center gap-2'
