# Secrets Directory

## Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Gmail API
4. Go to APIs & Services > Credentials
5. Create OAuth 2.0 Client ID (Application type: Desktop app)
6. Download the JSON file
7. Save it as `google.json` in this directory
8. Add the redirect URI in Google Console: `http://localhost:8000/auth/google/callback`

## Security Note

**DO NOT commit `google.json` to git!**

This directory is for local development only. The `.gitignore` file should exclude `*.json` files here.
