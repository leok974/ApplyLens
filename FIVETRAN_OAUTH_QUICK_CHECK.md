# 🔍 Fivetran Custom OAuth - Quick Verification

**Your Connector:** `exchanging_mantra` (Gmail)  
**Status:** ✅ Connected  
**Task:** Verify Custom OAuth is enabled

---

## ⚡ **Quick Check (2 minutes)**

### **Step 1: Open Fivetran**
```
https://fivetran.com/dashboard/connectors/exchanging_mantra
```

### **Step 2: Click "Setup" Tab**
- Look for OAuth section (usually near the bottom)

### **Step 3: Check for This:**

**✅ PASS - Custom OAuth:**
```
☑ Use your own OAuth app
   Client ID: 123456789012-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
   Client Secret: ••••••••••••••••••••
   Redirect URI: https://fivetran.com/auth/gmail
```

**❌ FAIL - Shared OAuth:**
```
☐ Use your own OAuth app
   [Using Fivetran's OAuth application]
```

---

## 📸 **Screenshot Needed**

Capture the OAuth section showing:
- ✅ "Use your own OAuth app" checkbox/toggle **CHECKED**
- ✅ Client ID visible (first 10-15 chars is enough)
- ✅ Client Secret shown as dots/asterisks

This proves Custom OAuth for Devpost submission.

---

## 🎯 **Expected Result**

If you followed the Fivetran setup guide (`analytics/fivetran/README.md`) and configured a Google OAuth client, you should see:

✅ Custom OAuth **enabled**  
✅ Your Google OAuth client ID displayed  
✅ Redirect URI pointing to Fivetran  

---

## ❓ **What If It's Using Shared OAuth?**

If "Use your own OAuth app" is **unchecked**, follow this guide to enable it:
- **Full Guide:** `docs/hackathon/FIVETRAN_OAUTH_VERIFY.md`
- **Section:** "How to Configure Custom OAuth"

**Quick Steps:**
1. Enable "Use your own OAuth app" in Fivetran
2. Get redirect URI from Fivetran
3. Create Google OAuth client with that redirect URI
4. Add client ID/secret to Fivetran
5. Re-authorize connector

---

## 📝 **Report Back**

After checking, update one of these:

**If Custom OAuth (PASS):**
```markdown
✅ Custom OAuth verified!
- Client ID starts with: [paste first 15 chars]
- Screenshot captured: Yes
- Ready for Devpost: Yes
```

**If Shared OAuth (FAIL):**
```markdown
❌ Using shared OAuth - need to configure
- Following guide: docs/hackathon/FIVETRAN_OAUTH_VERIFY.md
- Google OAuth client: [creating / created]
- ETA to fix: [estimate]
```

---

**Quick Link:** https://fivetran.com/dashboard/connectors/exchanging_mantra  
**Check:** Setup tab → OAuth section → "Use your own OAuth app"  
**Take:** Screenshot for evidence

---

**Status:** ⏳ Waiting for your UI check  
**Next:** Screenshot the OAuth section
