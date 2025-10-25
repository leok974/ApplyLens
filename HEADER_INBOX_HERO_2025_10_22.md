# Header Layout & Inbox Hero Logo - October 22, 2025

**Time**: 21:00 UTC
**Status**: ✅ Deployed

## Summary

Fixed header layout and added prominent inbox hero logo:
✅ 3-zone header (brand | tabs | actions) - no overlap
✅ Enlarged logo (28px → 32px)
✅ Scrollable tabs with hidden scrollbar
✅ Large inbox hero logo (112px-144px) on desktop
✅ Mobile-responsive (logo hidden <768px)

## Key Changes

### Header (AppHeader.tsx)
- Brand: `shrink-0` (pinned left, never collapses)
- Tabs: `flex-1 min-w-0 overflow-x-auto` (scrollable)
- Actions: `shrink-0` (pinned right)
- Logo: `h-7 w-7 md:h-8 md:w-8` (28px → 32px responsive)

### Inbox (Inbox.tsx)
- Added grid layout: `grid-cols-12 gap-4`
- Hero logo: `md:col-span-2` (hidden on mobile)
- Content: `md:col-span-10`
- Logo size: `h-28 w-28 xl:h-36 xl:w-36` (112px → 144px)
- Gradient halo effect around logo

### CSS (globals.css)
```css
.scrollbar-none {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-none::-webkit-scrollbar {
  display: none;
}
```

## Responsive Behavior

| Screen | Header Logo | Inbox Hero | Layout |
|--------|-------------|------------|--------|
| <768px | 28px | Hidden | Single column |
| 768-1280px | 32px | 112px | 2-col grid |
| >1280px | 32px | 144px | 2-col grid |

## Testing

**Playwright Test**: `apps/web/tests/ui/header-inbox.spec.ts`
- ✅ Brand positioned left (<40px from edge)
- ✅ Actions visible on right
- ✅ Hero logo >100px on desktop
- ✅ Tabs scrollable on narrow screens

## Deployment

```powershell
docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:latest apps/web/
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
# Status: Up 29 seconds (healthy) ✅
```

## Verify on Production

**URL**: https://applylens.app/inbox

- [ ] Header: Logo left, tabs center (scrollable), actions right
- [ ] No overlap at any screen size
- [ ] Large logo visible in inbox (desktop)
- [ ] Clean layout on mobile

## Files Modified

- `apps/web/src/components/AppHeader.tsx` - 3-zone layout
- `apps/web/src/pages/Inbox.tsx` - Hero logo section
- `apps/web/src/styles/globals.css` - Scrollbar utility
- `apps/web/tests/ui/header-inbox.spec.ts` - Layout tests

**Commit**: `feat(ui): tidy header spacing & add big inbox logo hero`
