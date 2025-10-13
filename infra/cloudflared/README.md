# Cloudflare Tunnel Setup Guide

## Prerequisites

- Cloudflare account with a domain (e.g., `applylens.app`)
- Domain's nameservers pointed to Cloudflare
- Docker and Docker Compose installed

## Setup Steps

### 1. Install Cloudflared

```bash
# On Windows (download from Cloudflare)
# Or pull the Docker image
docker pull cloudflare/cloudflared:latest
```

### 2. Authenticate to Cloudflare

```bash
# Run this locally or on your Docker host
# This opens a browser to authenticate
cloudflared tunnel login
```

This creates a certificate file at:

- **Windows**: `%USERPROFILE%\.cloudflared\cert.pem`
- **Linux**: `~/.cloudflared/cert.pem`

### 3. Create a Named Tunnel

```bash
# Create a tunnel named "applylens"
cloudflared tunnel create applylens

# This creates a credentials file with UUID
# Example: ~/.cloudflared/12345678-1234-1234-1234-123456789abc.json
```

### 4. Get Your Tunnel UUID

```bash
# List all tunnels to find your UUID
cloudflared tunnel list

# Example output:
# ID                                   NAME        CREATED
# 12345678-1234-1234-1234-123456789abc applylens   2025-10-11T10:30:00Z
```

### 5. Update Configuration

1. **Copy your tunnel UUID** from the output above

2. **Edit `infra/cloudflared/config.yml`**:
   - Replace `<YOUR_TUNNEL_UUID>` with your actual UUID (2 places)

3. **Copy credentials file**:

   ```bash
   # Copy the generated credentials file to this directory
   # Replace <YOUR_TUNNEL_UUID> with your actual UUID
   
   # Windows
   copy "%USERPROFILE%\.cloudflared\<YOUR_TUNNEL_UUID>.json" "infra\cloudflared\<YOUR_TUNNEL_UUID>.json"
   
   # Linux
   cp ~/.cloudflared/<YOUR_TUNNEL_UUID>.json infra/cloudflared/<YOUR_TUNNEL_UUID>.json
   ```

### 6. Create DNS Routes

```bash
# Main domain
cloudflared tunnel route dns applylens applylens.app

# www subdomain
cloudflared tunnel route dns applylens www.applylens.app

# Optional: Kibana dashboard
cloudflared tunnel route dns applylens kibana.applylens.app

# Optional: Grafana monitoring
cloudflared tunnel route dns applylens grafana.applylens.app
```

### 7. Update Docker Compose

The `cloudflared` service has been added to `docker-compose.yml`. Verify the configuration:

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  command: tunnel run applylens
  volumes:
    - ./cloudflared:/etc/cloudflared
  depends_on: [api]
  restart: unless-stopped
```

### 8. Start the Services

```bash
cd infra
docker compose up -d
```

### 9. Verify the Tunnel

```bash
# Check cloudflared logs
docker compose logs -f cloudflared

# Should see:
# "Connection registered" messages
# "Serving tunnel applylens"

# Test the endpoints
curl https://applylens.app/health
curl https://www.applylens.app/health
```

## Configuration Details

### Ingress Rules

The tunnel routes traffic based on hostname:

| Hostname | Service | Description |
|----------|---------|-------------|
| `applylens.app` | `http://api:8003` | Main API |
| `www.applylens.app` | `http://api:8003` | www subdomain |
| `kibana.applylens.app` | `http://kibana:5601` | Kibana dashboard (optional) |
| `grafana.applylens.app` | `http://grafana:3000` | Grafana (optional) |
| (catch-all) | `http_status:404` | 404 for unmatched |

### Network Architecture

```
Internet
    ↓
Cloudflare Edge
    ↓
Cloudflare Tunnel (encrypted)
    ↓
cloudflared container
    ↓
api:8003 (internal network)
```

**Key Benefits**:

- ✅ No public IP required
- ✅ No port forwarding needed
- ✅ Encrypted tunnel (TLS)
- ✅ DDoS protection via Cloudflare
- ✅ Free SSL/TLS certificates
- ✅ Works behind NAT/firewall

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check cloudflared logs
docker compose logs cloudflared

# Common issues:
# 1. Invalid tunnel UUID in config.yml
# 2. Credentials file not found
# 3. Wrong credentials file path
```

### DNS Not Resolving

```bash
# Verify DNS routes
cloudflared tunnel route dns list

# Should show:
# applylens.app -> applylens (your-tunnel-uuid)
```

### 502 Bad Gateway

```bash
# Check if API is running
docker compose ps api

# Check API logs
docker compose logs api

# Verify service name in config.yml matches docker-compose.yml
# Service name: "api" (not "applylens-api")
```

### Credentials File Issues

The credentials file must be:

- Named exactly: `<YOUR_TUNNEL_UUID>.json`
- Located in: `infra/cloudflared/`
- Referenced in `config.yml` with same UUID

## Security Considerations

### Protect Credentials

```bash
# Never commit credentials to git
# Add to .gitignore:
echo "infra/cloudflared/*.json" >> .gitignore
echo "infra/cloudflared/cert.pem" >> .gitignore

# Restrict file permissions (Linux)
chmod 600 infra/cloudflared/*.json
```

### Cloudflare Access (Optional)

Add authentication in front of your tunnel:

1. Go to Cloudflare Zero Trust dashboard
2. Create an Access Policy for `applylens.app`
3. Add authentication rules (email, OAuth, etc.)

### Rate Limiting

Configure rate limiting in Cloudflare dashboard:

- Security → WAF → Rate limiting rules
- Protect API endpoints from abuse

## Advanced Configuration

### Custom Origins

Add more services to `config.yml`:

```yaml
ingress:
  - hostname: api.applylens.app
    service: http://api:8003
  
  - hostname: es.applylens.app
    service: http://es:9200
    # Add authentication via Cloudflare Access!
  
  - hostname: static.applylens.app
    service: http://nginx:80
```

### Load Balancing

For high availability, run multiple cloudflared instances:

```yaml
# docker-compose.yml
cloudflared-1:
  image: cloudflare/cloudflared:latest
  command: tunnel run applylens
  volumes:
    - ./cloudflared:/etc/cloudflared
  depends_on: [api]
  restart: unless-stopped

cloudflared-2:
  image: cloudflare/cloudflared:latest
  command: tunnel run applylens
  volumes:
    - ./cloudflared:/etc/cloudflared
  depends_on: [api]
  restart: unless-stopped
```

Both replicas will connect to the same tunnel automatically.

### Monitoring

View tunnel metrics:

- Cloudflare dashboard → Zero Trust → Access → Tunnels
- Click on your tunnel to see:
  - Connection status
  - Traffic metrics
  - Request logs

## Maintenance

### Update Cloudflared

```bash
# Pull latest image
docker pull cloudflare/cloudflared:latest

# Restart tunnel
docker compose up -d cloudflared
```

### Rotate Credentials

```bash
# Delete old tunnel
cloudflared tunnel delete applylens

# Create new tunnel
cloudflared tunnel create applylens

# Update config.yml and credentials file
# Restart container
docker compose restart cloudflared
```

### Delete Tunnel

```bash
# Stop container
docker compose stop cloudflared

# Delete DNS routes
cloudflared tunnel route dns delete applylens applylens.app

# Delete tunnel
cloudflared tunnel delete applylens
```

## Production Checklist

- [ ] Tunnel created and UUID confirmed
- [ ] Credentials file copied to `infra/cloudflared/`
- [ ] `config.yml` updated with correct UUID
- [ ] DNS routes created for all hostnames
- [ ] Credentials file added to `.gitignore`
- [ ] `docker compose up -d` successful
- [ ] `docker compose logs cloudflared` shows "Connection registered"
- [ ] `curl https://applylens.app/health` returns 200
- [ ] SSL certificate valid (check in browser)
- [ ] (Optional) Cloudflare Access policies configured
- [ ] (Optional) Rate limiting rules configured
- [ ] Monitoring alerts set up for tunnel disconnections

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflared GitHub](https://github.com/cloudflare/cloudflared)
- [Zero Trust Dashboard](https://one.dash.cloudflare.com/)
