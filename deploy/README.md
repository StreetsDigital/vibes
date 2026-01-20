# Vibes Stack Deployment

Deploy the full vibes stack on a dedicated server or VPS.

## Quick Start

### 1. Provision a Server

Recommended specs for multi-agent work:

| Provider | Spec | Price | Agents |
|----------|------|-------|--------|
| Hetzner CPX31 | 4 vCPU, 8GB RAM | ~$15/mo | 3-5 |
| Hetzner AX42 | 6 cores, 64GB RAM | ~$55/mo | 10-20 |
| DigitalOcean | 4 vCPU, 8GB RAM | ~$48/mo | 3-5 |

### 2. Run Setup Script

SSH into your server and run:

```bash
# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/StreetsDigital/vibes/claude/evaluate-pageindex-zFMFu/deploy/setup-server.sh | sudo bash
```

Or manually:

```bash
git clone -b claude/evaluate-pageindex-zFMFu https://github.com/StreetsDigital/vibes.git
cd vibes/deploy
sudo ./setup-server.sh
```

### 3. Configure Environment

```bash
# Edit the environment file
sudo -u vibes nano /home/vibes/vibes/deploy/.env

# Required settings:
# - DOMAIN: Your domain (e.g., vibes.yourdomain.com)
# - ACME_EMAIL: For SSL certificates
# - ANTHROPIC_API_KEY: For Claude agents
# - POSTGRES_PASSWORD: Change from default!
```

### 4. Start the Stack

```bash
cd /home/vibes/vibes/deploy
docker compose up -d
```

### 5. Point DNS

Create these DNS records pointing to your server IP:

```
A     vibes.yourdomain.com      → YOUR_SERVER_IP
A     dash.vibes.yourdomain.com → YOUR_SERVER_IP
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Kanban | `https://vibes.yourdomain.com` | Visual task management |
| Dashboard | `https://dash.vibes.yourdomain.com` | Activity monitoring |
| Ollama | `https://ollama.vibes.yourdomain.com` | Local LLM (optional) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Internet                                                   │
│  └── Your Domain (vibes.yourdomain.com)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Caddy (Reverse Proxy)                                      │
│  ├── Automatic SSL via Let's Encrypt                       │
│  ├── Routes: / → kanban:3000                               │
│  └── Routes: /dash → dashboard:8080                        │
├─────────────────────────────────────────────────────────────┤
│  Docker Network                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Kanban     │ │  Dashboard  │ │  Ollama     │           │
│  │  :3000      │ │  :8080      │ │  :11434     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐                           │
│  │  PostgreSQL │ │   Redis     │                           │
│  │  :5432      │ │   :6379     │                           │
│  └─────────────┘ └─────────────┘                           │
├─────────────────────────────────────────────────────────────┤
│  Volumes                                                    │
│  ├── /home/vibes/projects     → Project git repos          │
│  ├── postgres_data            → Kanban database            │
│  └── ollama_data              → LLM models                 │
└─────────────────────────────────────────────────────────────┘
```

## Using Vibes on the Server

### Start a tmux Session

```bash
su - vibes
./start-vibes.sh
```

This creates a tmux session with:
- **Window 1 (claude)**: Claude Code CLI
- **Window 2 (shell)**: General shell
- **Window 3 (logs)**: Docker logs
- **Window 4 (monitor)**: htop

### Enable Beads (Git-backed Persistence)

Already enabled by default. Your features are stored in `.git/beads/` and survive crashes.

### Access from Phone (via Termius)

1. Install Tailscale on server: `sudo tailscale up`
2. Install Tailscale on phone
3. Connect via Termius to `vibes.your-tailnet.ts.net`

## Commands

```bash
# View logs
docker compose logs -f

# Restart services
docker compose restart

# Update stack
cd /home/vibes/vibes && git pull
docker compose pull
docker compose up -d

# Enable Ollama (for local LLM)
docker compose --profile with-ollama up -d

# Backup projects
tar -czf backup-$(date +%Y%m%d).tar.gz /home/vibes/projects
```

## Troubleshooting

### SSL Certificate Issues

```bash
# Check Caddy logs
docker compose logs caddy

# Force certificate renewal
docker compose exec caddy caddy reload
```

### Can't Connect to Services

```bash
# Check if services are running
docker compose ps

# Check firewall
sudo ufw status

# Verify DNS
dig vibes.yourdomain.com
```

### Out of Disk Space

```bash
# Clean Docker
docker system prune -a

# Check disk usage
df -h
du -sh /home/vibes/*
```

## Security

1. **Change default passwords** in `.env`
2. **Use Tailscale** for SSH instead of exposing port 22
3. **Enable 2FA** on your hosting provider
4. **Regular backups** of `/home/vibes/projects`

## Scaling with Fly.io Burst

For parallel agents without paying for idle capacity:

```
Base Server ($15/mo)          Fly.io (pay-per-use)
├── Mayor (orchestrator)      ├── Polecat-1 → Feature A
├── Kanban UI                 ├── Polecat-2 → Feature B
├── Dashboard                 ├── Polecat-3 → Feature C
└── Beads (git state)         └── (auto-shutdown when done)
```

### Setup Fly.io Burst

```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Login
fly auth login

# 3. Create app for Polecats
fly apps create vibes-polecats

# 4. Get API token
fly tokens create

# 5. Add to .env
FLY_API_TOKEN=your-token-here
FLY_APP_NAME=vibes-polecats
FLY_REGION=iad
```

### Cost Estimate

| Scenario | Base Server | Fly.io Burst | Total |
|----------|-------------|--------------|-------|
| Solo dev, occasional parallel | $15/mo | ~$5/mo | $20/mo |
| Heavy parallel (8hrs/day) | $15/mo | ~$20/mo | $35/mo |
| Team of 3 | $55/mo (AX42) | ~$30/mo | $85/mo |

Fly.io charges ~$0.02/hr per Polecat. A feature taking 15 mins = $0.005.

### How It Works

1. Mayor detects multiple pending Beads
2. Creates Convoy grouping related work
3. Spawns Polecat on Fly.io for each Convoy
4. Polecat clones repo, runs Claude, pushes changes
5. Polecat reports completion via webhook
6. Mayor pulls changes, updates Beads
7. Polecat auto-terminates (you stop paying)
