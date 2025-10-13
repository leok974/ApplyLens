# Cloudflare Tunnel Quick Start

## One-Time Setup (Run Once)

### Option 1: Automated Setup (Recommended)

**Windows PowerShell:**

```powershell
cd D:\ApplyLens\infra
.\setup-cloudflare-tunnel.ps1
```

**Linux/Mac:**

```bash
cd /path/to/ApplyLens/infra
chmod +x setup-cloudflare-tunnel.sh
./setup-cloudflare-tunnel.sh
```

The script will:

1. Authenticate you to Cloudflare
2. Create the tunnel
3. Copy credentials
4. Update configuration
5. Create DNS routes

### Option 2: Manual Setup

```bash
# 1. Login to Cloudflare
cloudflared tunnel login

# 2. Create tunnel
cloudflared tunnel create applylens

# 3. Get tunnel UUID
cloudflared tunnel list
# Copy the UUID (first column)

# 4. Copy credentials
# Windows:
copy "%USERPROFILE%\.cloudflared\<UUID>.json" "cloudflared\<UUID>.json"
# Linux/Mac:
cp ~/.cloudflared/<UUID>.json cloudflared/<UUID>.json

# 5. Edit cloudflared/config.yml
# Replace <YOUR_TUNNEL_UUID> with your actual UUID (2 places)

# 6. Create DNS routes (replace yourdomain.com)
cloudflared tunnel route dns applylens yourdomain.com
cloudflared tunnel route dns applylens www.yourdomain.com
```

## Daily Usage

### Start All Services

```bash
cd infra
docker compose up -d
```

### Start Just the Tunnel

```bash
docker compose up -d cloudflared
```

### Check Tunnel Status

```bash
docker compose logs -f cloudflared
```

### Stop Tunnel

```bash
docker compose stop cloudflared
```

### Restart Tunnel

```bash
docker compose restart cloudflared
```

## Verification

### Check Tunnel Connection

```bash
# Should show "Connection registered" messages
docker compose logs cloudflared | grep -i "connection"
```

### Test Your Endpoints

```bash
# Replace yourdomain.com with your actual domain
curl https://yourdomain.com/health
curl https://www.yourdomain.com/health
curl https://kibana.yourdomain.com
```

### View Tunnel in Cloudflare Dashboard

1. Go to <https://one.dash.cloudflare.com>
2. Navigate to: Access → Tunnels
3. Click on "applylens" tunnel
4. View status, traffic, and logs

## Troubleshooting

### Tunnel Won't Start

```bash
# Check configuration
cat cloudflared/config.yml

# Verify UUID matches credentials file
ls -la cloudflared/

# Check docker logs
docker compose logs cloudflared
```

### 502 Bad Gateway

```bash
# Ensure API is running
docker compose ps api

# Check API logs
docker compose logs api

# Verify service names in config.yml match docker-compose.yml
```

### DNS Not Resolving

```bash
# List DNS routes
cloudflared tunnel route dns list

# Should show your domain → applylens tunnel
```

### Re-authenticate

```bash
# If authentication expired
cloudflared tunnel login
```

## Configuration Files

```
infra/
├── cloudflared/
│   ├── config.yml           # Tunnel configuration
│   ├── <UUID>.json          # Credentials (DO NOT COMMIT)
│   ├── README.md            # Full documentation
│   └── .gitkeep             # Setup instructions
├── docker-compose.yml       # Includes cloudflared service
└── setup-cloudflare-tunnel.* # Automated setup scripts
```

## Common Commands

| Task | Command |
|------|---------|
| List tunnels | `cloudflared tunnel list` |
| View DNS routes | `cloudflared tunnel route dns list` |
| Delete DNS route | `cloudflared tunnel route dns delete applylens yourdomain.com` |
| Delete tunnel | `cloudflared tunnel delete applylens` |
| Update cloudflared | `docker pull cloudflare/cloudflared:latest && docker compose up -d cloudflared` |

## Architecture

```
Internet → Cloudflare Edge → Encrypted Tunnel → cloudflared container → api:8003
```

**Benefits:**

- ✅ No public IP needed
- ✅ No port forwarding
- ✅ Free SSL/TLS
- ✅ DDoS protection
- ✅ Works behind NAT

## Next Steps

1. ✅ Complete setup (use automated script)
2. ✅ Start tunnel: `docker compose up -d`
3. ✅ Verify: `docker compose logs cloudflared`
4. ✅ Test: `curl https://yourdomain.com/health`
5. 📝 (Optional) Add Cloudflare Access for authentication
6. 📝 (Optional) Configure rate limiting
7. 📝 (Optional) Set up monitoring alerts

See `cloudflared/README.md` for detailed documentation.
