# OAuth Quick Reference Card

One-page cheat sheet for OAuth configuration to fix `redirect_uri_mismatch`.

---

## 🎯 Quick Fix

### 1. Google Cloud Console

**Add these Authorized redirect URIs:**
```
https://api.applylens.app/auth/google/callback
http://localhost:8003/auth/google/callback
```

**Add these Authorized JavaScript origins:**
```
https://applylens.app
http://localhost:5175
```

### 2. Environment Variables

**Local (.env):**
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI_DEV=http://localhost:8003/auth/google/callback
```

**Production (.env.prod):**
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://api.applylens.app/auth/google/callback
```

### 3. Restart Services

```bash
cd infra
docker compose restart api nginx
```

---

## 📋 Configuration URLs

### Local Development
- **API**: http://localhost:8003
- **Web**: http://localhost:5175
- **Login**: http://localhost:8003/auth/google/login
- **Callback**: http://localhost:8003/auth/google/callback

### Production
- **API**: https://api.applylens.app
- **Web**: https://applylens.app
- **Login**: https://api.applylens.app/auth/google/login
- **Callback**: https://api.applylens.app/auth/google/callback

---

## 🧪 Testing

### Manual Test
```bash
# 1. Start services
docker compose up -d

# 2. Check config
docker compose exec api python -c "
from app.settings import settings
print(f'Redirect URI: {settings.effective_redirect_uri}')
"

# 3. Open browser
open http://localhost:8003/auth/google/login
```

### Automated Test
```powershell
# Run smoke tests
.\scripts\smoke-applylens.ps1

# Expected:
# ✅ OAuth login redirects to Google (HTTP 302)
# ✅ OAuth callback route is accessible
```

---

## 🐛 Troubleshooting

### Still seeing redirect_uri_mismatch?

**1. Check Google Cloud Console:**
- URI must match **exactly** (no trailing slash)
- Check for http vs https
- Check for correct port

**2. Check environment variables:**
```bash
docker compose exec api env | grep GOOGLE
```

**3. Check logs:**
```bash
docker compose logs api | grep OAuth
# Should show: [OAuth] Initiating login flow with redirect_uri: ...
```

**4. Verify Nginx:**
```bash
docker compose exec nginx nginx -t
docker compose restart nginx
```

**5. Clear browser cache and try again**

---

## 🔑 Environment Variable Priority

1. `GOOGLE_REDIRECT_URI` (production)
2. `GOOGLE_REDIRECT_URI_DEV` (fallback for local)
3. Default: `http://localhost:8003/auth/google/callback`

---

## 📚 Full Documentation

See `infra/docs/OAUTH_SETUP.md` for complete guide.

---

## ✅ Checklist

Setup:
- [ ] OAuth client created in Google Cloud Console
- [ ] Redirect URIs added (prod + dev)
- [ ] Client ID and Secret copied
- [ ] Environment variables set
- [ ] google.json file in /secrets/
- [ ] Services restarted

Testing:
- [ ] Manual OAuth flow works
- [ ] Smoke tests pass
- [ ] Logs show correct redirect_uri
- [ ] No 400 errors

---

**One-liner commands:**

```bash
# Check config
docker compose exec api python -c "from app.settings import settings; print(settings.effective_redirect_uri)"

# Restart services
docker compose restart api nginx

# Test login
curl -I http://localhost:8003/auth/google/login

# Run smoke tests
.\scripts\smoke-applylens.ps1

# View logs
docker compose logs -f api | grep OAuth
```

---

**Last Updated**: 2025-10-11  
**Print this for quick reference!**
