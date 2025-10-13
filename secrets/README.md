# Secrets Directory

This directory contains OAuth credentials and other sensitive configuration files.

## ⚠️ IMPORTANT: Do NOT commit actual secrets to git

All files in this directory (except `.example` files) are ignored by git.

## Setup Instructions

### 1. Google OAuth Credentials

1. Copy `google.json.example` to `google.json`:

   ```bash
   cp google.json.example google.json
   ```

2. Go to [Google Cloud Console](https://console.cloud.google.com/)
3. Create a new project or select an existing one
4. Enable the Gmail API
5. Create OAuth 2.0 credentials (OAuth client ID)
6. Download the credentials JSON file
7. Copy the contents to `google.json`

### 2. File Structure

```text
secrets/
├── .gitkeep
├── README.md           # This file
├── google.json.example # Template for Google OAuth credentials
└── google.json         # YOUR ACTUAL CREDENTIALS (gitignored)
```text

## Security Notes

- ✅ `.example` files are committed (safe templates)
- ❌ Actual credential files are **NOT** committed (in .gitignore)
- 🔒 Never share actual credentials in public repositories
- 🔄 Rotate credentials if accidentally exposed

## See Also

- [docs/OAUTH_SETUP_COMPLETE.md](../docs/OAUTH_SETUP_COMPLETE.md) - Complete OAuth setup guide
- [docs/GMAIL_SETUP.md](../docs/GMAIL_SETUP.md) - Gmail integration setup
