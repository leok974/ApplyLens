# ApplyLens - Quick Reference

## 🚀 Quick Start Commands

### Initial Setup

```bash
# 1. Copy environment file
cp infra/.env.example infra/.env

# 2. Add OAuth secret (generate random string)
# Edit infra/.env and set OAUTH_STATE_SECRET

# 3. Start services
docker compose -f infra/docker-compose.yml up -d

# 4. Wait for services (takes ~30 seconds)
docker compose -f infra/docker-compose.yml ps
```text

### Gmail Integration

```bash
# 1. Get OAuth credentials from Google Cloud Console
# 2. Save as infra/secrets/google.json
# 3. Visit: http://localhost:8003/auth/google/login
# 4. Sync emails via UI or:
curl -X POST "http://localhost:8003/gmail/backfill?days=60&user_email=your@gmail.com"
```text

## 📍 URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Web App** | <http://localhost:5175> | Main UI |
| **API Docs** | <http://localhost:8003/docs> | Swagger UI |
| **Elasticsearch** | <http://localhost:9200> | Search engine |
| **Kibana** | <http://localhost:5601> | Analytics dashboard |
| **Gmail Auth** | <http://localhost:8003/auth/google/login> | OAuth flow |

## 🔧 Common Commands

### Docker Management

```bash
# View logs
docker compose -f infra/docker-compose.yml logs api --tail=50
docker compose -f infra/docker-compose.yml logs web --tail=50

# Restart services
docker compose -f infra/docker-compose.yml restart api
docker compose -f infra/docker-compose.yml restart web

# Stop all services
docker compose -f infra/docker-compose.yml down

# Rebuild after code changes
docker compose -f infra/docker-compose.yml build api
docker compose -f infra/docker-compose.yml up -d api
```text

### Database

```bash
# Run migrations
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# Create new migration
docker compose -f infra/docker-compose.yml exec api alembic revision --autogenerate -m "Description"

# Access database
docker compose -f infra/docker-compose.yml exec db psql -U postgres -d applylens

# Check OAuth tokens
docker compose -f infra/docker-compose.yml exec db psql -U postgres -d applylens -c "SELECT user_email, provider, expiry FROM oauth_tokens;"
```text

### Elasticsearch

```bash
# Check index
curl http://localhost:9200/gmail_emails/_count

# View mappings
curl http://localhost:9200/gmail_emails/_mapping

# Delete and recreate index
curl -X DELETE http://localhost:9200/gmail_emails
docker compose -f infra/docker-compose.yml restart api
```text

### Testing

```bash
# Run unit tests
docker compose -f infra/docker-compose.yml exec api pytest tests/ -v

# Test search endpoint
curl "http://localhost:8003/search/?q=interview"

# Test with label filter
curl "http://localhost:8003/search/?q=interview&label_filter=interview"

# Test autocomplete
curl "http://localhost:8003/suggest/?q=interv"

# Test Gmail status
curl http://localhost:8003/gmail/status

# Test inbox (requires auth)
curl "http://localhost:8003/gmail/inbox?page=1&limit=10"
```text

## 📧 Email Labels

| Label | Icon | Description | Keywords |
|-------|------|-------------|----------|
| `interview` | 📅 | Interview invitations | interview, phone screen, onsite |
| `offer` | 🎉 | Job offers | offer, offer letter, acceptance |
| `rejection` | ❌ | Rejection emails | not selected, regret to inform |
| `application_receipt` | ✅ | Application confirmations | application received, submitted |
| `newsletter_ads` | 📰 | Promotional content | unsubscribe, newsletter, noreply |

## 🔍 Search Examples

```bash
# Basic search
curl "http://localhost:8003/search/?q=Interview"

# Filter by label
curl "http://localhost:8003/search/?q=engineer&label_filter=interview"

# Synonym matching (automatically matches)
curl "http://localhost:8003/search/?q=talent%20partner"  # matches "recruiter"
curl "http://localhost:8003/search/?q=phone%20screen"    # matches "interview"

# Autocomplete
curl "http://localhost:8003/suggest/?q=Interv"
```text

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
netstat -ano | findstr :8003

# Or change the port in infra/.env
API_PORT=8004
```text

### API Won't Start

```bash
# Check logs
docker compose -f infra/docker-compose.yml logs api --tail=100

# Common issues:
# - Database not ready: wait 10 seconds and try again
# - Missing dependencies: rebuild container
docker compose -f infra/docker-compose.yml build --no-cache api
docker compose -f infra/docker-compose.yml up -d api
```text

### Gmail Auth Not Working

```bash
# Verify secrets file exists
ls infra/secrets/google.json

# Check OAuth redirect URI in Google Console matches:
# http://localhost:8003/auth/google/callback

# Verify environment variables
docker compose -f infra/docker-compose.yml exec api env | grep GOOGLE
```text

### No Emails Showing

```bash
# Check connection status
curl http://localhost:8003/gmail/status

# If not connected, visit:
open http://localhost:8003/auth/google/login

# After connecting, sync emails:
curl -X POST "http://localhost:8003/gmail/backfill?days=7&user_email=your@gmail.com"
```text

### Elasticsearch Issues

```bash
# Check ES health
curl http://localhost:9200/_cluster/health

# Verify index exists
curl http://localhost:9200/_cat/indices

# Recreate index
# Set ES_RECREATE_ON_START=true in infra/.env, then:
docker compose -f infra/docker-compose.yml restart api
```text

## 🔐 Security Checklist

- [ ] Change `OAUTH_STATE_SECRET` to a random 32+ character string
- [ ] Never commit `infra/secrets/google.json` to git
- [ ] Use HTTPS in production (update `OAUTH_REDIRECT_URI`)
- [ ] Review Google OAuth scopes (currently read-only)
- [ ] Enable database encryption for production
- [ ] Set up firewall rules for Elasticsearch/Kibana
- [ ] Implement rate limiting on API endpoints
- [ ] Add user authentication for multi-user setups

## 📚 Additional Resources

- Full Gmail setup guide: [`GMAIL_SETUP.md`](./GMAIL_SETUP.md)
- Main README: [`README.md`](./README.md)
- API documentation: <http://localhost:8003/docs>
- Google OAuth guide: <https://developers.google.com/identity/protocols/oauth2>

## 🆘 Getting Help

1. Check the logs: `docker compose -f infra/docker-compose.yml logs api web`
2. View API docs: <http://localhost:8003/docs>
3. Test endpoints with Swagger UI
4. Review the setup guides in the repository
