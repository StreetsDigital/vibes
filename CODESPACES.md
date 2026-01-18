# GitHub Codespaces Setup

**Run vibecoding-stack in the cloud with Docker - FREE and zero local setup!**

---

## Why Codespaces?

✅ **Free:** 120 core-hours/month (60 hours on 2-core)
✅ **Docker included:** Already running, no installation
✅ **Zero setup:** Everything auto-installs
✅ **No local resources:** Your machine stays clean
✅ **Access anywhere:** Browser or VS Code

---

## Quick Start (3 Steps)

### 1. Push to GitHub

```bash
cd vibecoding-stack
git init
git add .
git commit -m "Initial vibecoding-stack setup"
git remote add origin https://github.com/YOUR-USERNAME/vibecoding-stack.git
git push -u origin master
```

### 2. Create Codespace

**Option A: From GitHub Website**
1. Go to your repo: `https://github.com/YOUR-USERNAME/vibecoding-stack`
2. Click green **"Code"** button
3. Click **"Codespaces"** tab
4. Click **"Create codespace on master"**

**Option B: Direct URL**
```
https://github.com/codespaces/new?repo=YOUR-USERNAME/vibecoding-stack
```

### 3. Wait for Auto-Setup (2 minutes)

The Codespace will automatically:
- ✅ Install Docker
- ✅ Install Python dependencies
- ✅ Install ClaudeBox
- ✅ Make `vibecode` command available
- ✅ Set up environment

When you see:
```
╔══════════════════════════════════════════════════════════════╗
║     SETUP COMPLETE!                                          ║
╚══════════════════════════════════════════════════════════════╝
```

You're ready!

---

## Start Coding

In the Codespace terminal:

```bash
# Create your first isolated project
vibecode new my-api python

# Start coding
vibecode code my-api
```

That's it! Docker is running in the cloud, Claude Code works locally or in the browser.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  GITHUB CODESPACE (Cloud VM)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Docker (pre-installed)                               │  │
│  │  ├─ Container: my-api (Python)                        │  │
│  │  ├─ Container: my-frontend (JavaScript)               │  │
│  │  └─ Container: my-service (Go)                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  vibecoding-stack/ (your code)                              │
│  ├─ vibecode (command)                                      │
│  ├─ .devcontainer/ (auto-setup config)                      │
│  └─ projects managed by ClaudeBox                           │
└─────────────────────────────────────────────────────────────┘
         ↕
    VS Code (local or browser)
```

---

## Daily Workflow

### Morning: Open Codespace

```bash
# From command line (if you have GitHub CLI)
gh codespace list
gh codespace code -c YOUR-CODESPACE-NAME

# Or from website
# https://github.com/codespaces
```

### Work on Projects

```bash
# List projects
vibecode list

# Work on API
vibecode code my-api

# Switch to frontend (zero bleed!)
vibecode code my-frontend
```

### Evening: Stop Codespace

Codespaces auto-stop after 30 minutes of inactivity (configurable).

Or manually:
- **Browser:** File → Stop Codespace
- **CLI:** `gh codespace stop -c YOUR-CODESPACE-NAME`

---

## Free Tier Limits

**What you get:**
- 120 core-hours/month FREE
- 2-core machine = 60 hours/month
- 4-core machine = 30 hours/month
- 15 GB storage

**Tips to maximize free tier:**
1. Use 2-core machine (default)
2. Stop Codespace when not coding
3. Delete old Codespaces you don't need
4. Auto-stop after 30 min (default is good)

**Usage calculator:**
- 2 hours/day × 5 days/week = 40 hours/month ✅ Well within free tier!

---

## Configuration

The setup is defined in `.devcontainer/devcontainer.json`:

```json
{
  "name": "Vibecoding Stack",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "docker-in-docker": {}  // ← Docker support
  },
  "postCreateCommand": "bash .devcontainer/setup.sh"  // ← Auto-setup
}
```

Auto-setup script: `.devcontainer/setup.sh`

---

## Customization

### Change Machine Size

In GitHub repo settings:
1. Settings → Codespaces
2. Change default machine type
3. Options: 2-core, 4-core, 8-core

### Pre-install More Tools

Edit `.devcontainer/setup.sh`:

```bash
# Add your tools
sudo apt-get install -y jq tree htop
pip install your-favorite-package
```

### VS Code Extensions

Edit `.devcontainer/devcontainer.json`:

```json
"customizations": {
  "vscode": {
    "extensions": [
      "ms-python.python",
      "your.extension"
    ]
  }
}
```

---

## Multiple Projects

You can run multiple Codespaces simultaneously:

```bash
# Codespace 1: Client A work
vibecode new client-a-api python
vibecode code client-a-api

# Codespace 2: Client B work (separate Codespace!)
vibecode new client-b-api go
vibecode code client-b-api

# Complete isolation, even between Codespaces!
```

---

## Access from Local VS Code

**Better experience than browser:**

1. Install VS Code extension: `GitHub Codespaces`
2. Open VS Code
3. `Cmd+Shift+P` → "Codespaces: Connect to Codespace"
4. Select your Codespace
5. Full VS Code experience with cloud Docker!

---

## Troubleshooting

### "Docker not ready"

Wait 1-2 minutes after Codespace starts. Docker needs time to initialize.

```bash
# Check Docker status
docker info

# If not ready, wait and retry
```

### "vibecode: command not found"

Reload terminal:

```bash
source ~/.bashrc
vibecode help
```

### Setup didn't run

Manually trigger:

```bash
bash .devcontainer/setup.sh
```

### Storage full

Delete old containers:

```bash
vibecode remove old-project
docker system prune -a
```

---

## Costs (if you go over free tier)

| Machine | Price/hour | Free hours/month | Cost if 100 hrs/month |
|---------|-----------|------------------|---------------------|
| 2-core  | $0.18     | 120              | $0 (within free)    |
| 4-core  | $0.36     | 120              | $7.20 over          |
| 8-core  | $0.72     | 120              | $21.60 over         |

**Recommendation:** Stick with 2-core for free usage.

---

## Benefits Over Local Docker

| Aspect | Local Docker | Codespaces |
|--------|-------------|------------|
| Setup | Install & configure | Instant |
| Resources | Uses your RAM/CPU | Cloud resources |
| Cost | $0 | $0 (with free tier) |
| Access | One machine only | Anywhere |
| Cleanup | Manual | Auto-managed |
| Machine stress | High | Zero |

---

## Pro Tips

1. **Use Codespace prebuilds:** Speed up creation (GitHub Pro feature)
2. **Commit often:** Codespaces are ephemeral
3. **Use Codespace secrets:** For API keys, tokens
4. **Stop when done:** Maximize free hours
5. **Name your Codespaces:** Easy to find later

---

## Next Steps

1. **Push to GitHub** (if you haven't)
2. **Create Codespace**
3. **Wait for auto-setup**
4. **Run:** `vibecode new my-first-project python`
5. **Read:** `GETTING_STARTED.md` for workflows

---

## Alternative: Gitpod

If you prefer Gitpod (50 hours/month free):

1. Create `.gitpod.yml`:
```yaml
image: gitpod/workspace-full

tasks:
  - init: bash .devcontainer/setup.sh
```

2. Open: `https://gitpod.io/#https://github.com/YOUR-REPO/vibecoding-stack`

Same setup, different platform!

---

**You now have a cloud-based vibecoding environment with Docker, completely free! 🎉**

No more Docker on your local machine!
