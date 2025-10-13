# ApplyLens Quick Reference

**Quick commands for daily operations**

## 🚀 Start/Stop

```powershell
# Start all services
cd D:\ApplyLens\infra
docker compose up -d

# Stop all services
docker compose down

# View status
docker compose ps
```text

## 📧 Sync Gmail

```powershell
# Check connection
curl http://localhost:8003/gmail/status

# Manual sync (2 days)
Invoke-RestMethod -Uri "http://localhost:8003/gmail/backfill?days=2" -Method POST

# Full resync (60 days)
Invoke-RestMethod -Uri "http://localhost:8003/gmail/backfill?days=60" -Method POST

# Check scheduled task
Get-ScheduledTask -TaskName "ApplyLens-GmailSync"
```text

## 🔐 OAuth Issues

```powershell
# Re-authenticate
start http://localhost:8003/auth/google/login

# Remove old permissions
start https://myaccount.google.com/permissions
```text

## 📊 Data Counts

```powershell
# Emails
curl http://localhost:8003/gmail/status

# Applications
curl http://localhost:8003/applications | ConvertFrom-Json | Measure-Object

# Elasticsearch
curl http://localhost:9200/gmail_emails/_count
```text

## 🔍 Search

```powershell
# Search emails
curl "http://localhost:8003/search?q=interview"

# Filter applications
curl "http://localhost:8003/applications?status=interview"
curl "http://localhost:8003/applications?company=Google"
```text

## 🎨 Web UI

- Inbox: <http://localhost:5175/inbox>
- Tracker: <http://localhost:5175/tracker>
- Settings: <http://localhost:5175/settings>

## 📝 Logs

```powershell
# API logs (follow)
docker compose logs -f api

# Last 50 lines
docker compose logs api --tail=50

# Errors only
docker compose logs api --tail=100 | Select-String -Pattern "error|exception"
```text

## 🛠️ Troubleshooting

```powershell
# Restart API
docker compose restart api

# Check ES health
curl http://localhost:9200/_cluster/health

# Test database
docker compose exec db psql -U postgres -d applylens -c "SELECT 1;"

# View scheduled task history
Get-ScheduledTask -TaskName "ApplyLens-GmailSync" | Get-ScheduledTaskInfo
```text

## 💾 Backup

```powershell
# Export applications
curl http://localhost:8003/applications | Out-File -FilePath "backup-$(Get-Date -Format 'yyyy-MM-dd').json"

# Database backup
docker compose exec db pg_dump -U postgres applylens > "backup-db-$(Get-Date -Format 'yyyy-MM-dd').sql"
```text

---

**Full Documentation:** See `PRODUCTION_SETUP.md`  
**User:** <leoklemet.pa@gmail.com>  
**Status:** ✅ Operational
