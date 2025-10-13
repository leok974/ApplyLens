# Security Search Filters - Quick Start Guide

## 🎯 Overview

Security search filters allow you to quickly find high-risk and quarantined emails using visual toggle chips.

## 🚀 Usage

### High-Risk Filter (≥80)

**What it does:** Shows only emails with risk score ≥ 80

**How to use:**
1. Navigate to `/search`
2. Click the "High Risk (≥80)" chip
3. Results automatically update

**URL Example:**
```
/search?q=invoice&risk_min=80
```

### Quarantined Only Filter

**What it does:** Shows only quarantined emails

**How to use:**
1. Navigate to `/search`
2. Click the "Quarantined only" chip
3. Results automatically update

**URL Example:**
```
/search?q=test&quarantined=true
```

### Using Both Filters

**What it does:** Shows emails that are BOTH high-risk AND quarantined

**How to use:**
1. Toggle both chips ON
2. Results match all active filters

**URL Example:**
```
/search?q=security&risk_min=80&quarantined=true
```

## 🎨 Visual Guide

### Filter Chips

```
┌─────────────────────────────────────────────────────┐
│  🛡️ Security filters:                               │
│                                                      │
│  [🔴 High Risk (≥80)]  [🟡 Quarantined only]       │
│   Toggle ON for red    Toggle ON for amber          │
│   Toggle OFF for gray  Toggle OFF for gray          │
└─────────────────────────────────────────────────────┘
```

### Active State
- **High-Risk Chip:** Red background, red border, red text
- **Quarantined Chip:** Amber background, amber border, amber text
- **Switch:** Shows as "on" (right position)

### Inactive State
- **Both Chips:** Gray background, subtle border, default text
- **Switch:** Shows as "off" (left position)

## 🔗 URL Parameters

| Filter | URL Parameter | Example Value |
|--------|---------------|---------------|
| High-Risk | `risk_min` | `80` |
| Quarantined | `quarantined` | `true` |

**Shareable URLs:**
Copy the URL from your browser to share filtered search results with others!

## ⚡ Keyboard Shortcuts

- **Enter** in search box: Execute search with current filters
- **Tab** to chips, **Space** to toggle

## 🧪 Testing

### Run E2E Tests
```bash
npm run test:e2e -- security-search-filters.spec.ts
```

### Manual Test Checklist
- [ ] Click High-Risk chip → URL updates → Results filter
- [ ] Click Quarantined chip → URL updates → Results filter
- [ ] Click both chips → Both filters active
- [ ] Click "Clear filters" → All filters removed
- [ ] Refresh page → Filters persist from URL
- [ ] Copy URL → Open in new tab → Filters applied

## 📊 API Integration

### Request Format
```bash
# High-risk emails
curl "http://localhost:8003/api/search/?q=invoice&risk_min=80"

# Quarantined emails
curl "http://localhost:8003/api/search/?q=test&quarantined=true"

# Both filters
curl "http://localhost:8003/api/search/?q=security&risk_min=80&quarantined=true"
```

### Response Format
```json
{
  "hits": [
    {
      "id": "123",
      "subject": "Suspicious invoice",
      "from_addr": "attacker@evil.com",
      "risk_score": 85,
      "quarantined": true,
      "score": 0.95,
      "received_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

## 🎓 Examples

### Example 1: Find All High-Risk Emails
```
1. Go to /search
2. Clear search box (or search for "*")
3. Toggle "High Risk (≥80)" ON
4. View all high-risk emails
```

### Example 2: Review Quarantined Invoices
```
1. Go to /search
2. Type "invoice" in search box
3. Toggle "Quarantined only" ON
4. Press Enter
5. Review quarantined invoice emails
```

### Example 3: Investigate Critical Threats
```
1. Go to /search
2. Type "phishing" or "suspicious"
3. Toggle BOTH chips ON
4. View emails that are both high-risk and quarantined
```

### Example 4: Share Filtered Results
```
1. Apply your desired filters
2. Copy URL from browser address bar
3. Send to colleague
4. They see same filtered results when they open the link
```

## 🔧 Troubleshooting

**Q: Filters not working?**
- Check that backend migration 0015 is applied
- Verify API container is running
- Check browser console for errors

**Q: URL not updating?**
- Hard refresh the page (Ctrl+Shift+R)
- Clear browser cache
- Check JavaScript errors in console

**Q: Results not changing?**
- Verify backend has security fields (`risk_score`, `quarantined`)
- Check API logs for query handling
- Ensure Elasticsearch index has security mappings

## 📚 Related Documentation

- [SECURITY_SEARCH_FILTERS.md](./SECURITY_SEARCH_FILTERS.md) - Full technical documentation
- [DEPLOYMENT_BACKEND_ENHANCEMENTS.md](../DEPLOYMENT_BACKEND_ENHANCEMENTS.md) - Backend security features
- [SECURITY_UI_IMPLEMENTATION.md](../SECURITY_UI_IMPLEMENTATION.md) - Security UI components

## 💡 Tips

1. **Combine with other filters:** Security filters work alongside category, label, and date filters
2. **Use URL bookmarks:** Save frequently used filter combinations as browser bookmarks
3. **Share filtered views:** Send URLs to team members for collaborative review
4. **Clear when done:** Use "Clear filters" button to reset to default view

## ✅ Done!

You're now ready to use security search filters! Start by navigating to `/search` and exploring the new chips.
