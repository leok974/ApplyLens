# Extension Assets

This folder contains screenshots and promotional images for the Chrome Web Store listing.

## Required Files

### Screenshots (1280x800 PNG)
- **screen1.png** - Scan forms & suggest answers
  - Show the extension popup with "Scan form & suggest" button
  - Show a Greenhouse/Lever form with autofilled fields
  - Highlight the key value: automatic field population

- **screen2.png** - Draft recruiter DMs
  - Show LinkedIn profile page
  - Show the extension popup with "Draft recruiter DM" button
  - Show the drafted message copied to clipboard

- **screen3.png** - Browser Companion settings & activity
  - Show the `/settings/companion` page from the web app
  - Display the recent applications and outreach tables
  - Show API connectivity status

### Promotional Tile (1280x800 PNG)
- **promo-1280x800.png** - Store listing promotional image
  - Eye-catching design with ApplyLens branding
  - Highlight key features: Autofill, DM generation, Privacy-first
  - Include call-to-action text

## Screenshot Tips

1. **Use realistic data** - Show actual company names and job titles
2. **Clean UI** - Remove any sensitive information or test data
3. **High quality** - Use 2x resolution for crisp display
4. **Annotations** - Add arrows/highlights to draw attention to key features
5. **Consistent branding** - Use ApplyLens colors and design system

## Generating Screenshots

### Option 1: Manual (Recommended)
1. Load the extension in Chrome
2. Open a real job application page (Greenhouse, Lever, etc.)
3. Use browser DevTools (Cmd+Shift+5 on Mac, Win+Shift+S on Windows)
4. Crop to exactly 1280x800 pixels

### Option 2: Playwright
Create a Playwright test that navigates to the pages and takes screenshots:
```typescript
await page.setViewportSize({ width: 1280, height: 800 });
await page.goto('/extension');
await page.screenshot({ path: 'screen1.png' });
```

## Current Status
- [ ] screen1.png - Placeholder needed
- [ ] screen2.png - Placeholder needed
- [ ] screen3.png - Placeholder needed
- [ ] promo-1280x800.png - Placeholder needed

## Upload to Chrome Web Store
After creating these files:
1. Upload to Chrome Developer Dashboard
2. Ensure they display correctly in the store preview
3. Update if rejected by review team
