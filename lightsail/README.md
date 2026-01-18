# Vibecoding on Lightsail + Termius

Code from your phone using AWS Lightsail and Termius.

## Quick Setup

### 1. Create Lightsail Instance

**AWS Console > Lightsail > Create Instance**

| Setting | Recommended |
|---------|-------------|
| Region | Closest to you |
| OS | Ubuntu 22.04 LTS |
| Plan | $5/mo (1GB RAM) or $10/mo (2GB) |
| Name | `vibecode` |

### 2. Download SSH Key

After creating the instance:
1. Go to **Account > SSH keys**
2. Download the default key (or create a new one)
3. Save it - you'll add this to Termius

### 3. Run Setup Script

SSH into your instance and run:

```bash
# Option A: One-liner
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/vibes/main/lightsail/setup.sh | bash

# Option B: Clone and run
git clone https://github.com/YOUR_REPO/vibes.git
cd vibes/lightsail
chmod +x setup.sh
./setup.sh
```

### 4. Configure Termius

#### Add SSH Key
1. Open Termius > Settings > Keys
2. Import Key > paste your Lightsail private key
3. Name it `lightsail`

#### Add Host
1. Hosts > + (add new)
2. Configure:
   - **Label**: `vibecode`
   - **Address**: Your Lightsail public IP
   - **Port**: 22
   - **Username**: `ubuntu` (or your user)
   - **Key**: Select `lightsail`

---

## Daily Workflow

### Start Coding

```bash
# Connect via Termius, then:
vibe my-project    # Creates/attaches to tmux session
claude             # Start Claude Code
```

### Window Layout

Each session has 4 windows:

| Window | Name | Purpose |
|--------|------|---------|
| 1 | `claude` | Main Claude Code session |
| 2 | `shell` | Git, npm, terminal commands |
| 3 | `logs` | Watch builds, tests, output |
| 4 | `scratch` | Exploration & experiments |

Switch with `Ctrl+a 1` through `Ctrl+a 4`.

### Detach When Done

Press `Ctrl+a` then `d` to detach. Your session keeps running!

### Resume Later

```bash
vibe my-project    # Reattaches to your running session
```

---

## tmux Cheatsheet (Mobile-Optimized)

Prefix key: `Ctrl+a`

### Sessions
| Keys | Action |
|------|--------|
| `Ctrl+a d` | Detach (keeps running) |
| `Ctrl+a S` | New session |
| `Ctrl+a K` | Kill session |

### Windows
| Keys | Action |
|------|--------|
| `Ctrl+a c` | New window |
| `Ctrl+a 1-4` | Switch to window 1-4 |
| `Ctrl+a ,` | Rename window |

### Panes
| Keys | Action |
|------|--------|
| `Ctrl+a \|` | Split horizontal |
| `Ctrl+a -` | Split vertical |
| `Ctrl+a ←↑↓→` | Navigate panes |
| `Ctrl+a Ctrl+a` | Zoom/unzoom pane |

### Termius Tip
Use Termius's built-in keyboard toolbar for special keys like `Ctrl`, `Esc`, and arrows.

---

## File Structure

After setup:
```
~/
├── bin/
│   ├── vibe           # Session starter
│   ├── vibe-list      # List sessions
│   └── vibe-kill      # Kill session
├── projects/          # Your code lives here
├── vibecoding/
│   └── autocoder/     # Feature queue system
└── .tmux.conf         # Mobile-optimized config
```

---

## Tips for Phone Coding

### Termius Settings
- Enable **Extended Keyboard** for special keys
- Turn on **Keep Alive** to prevent disconnects
- Use **Snippets** for common commands

### Recommended Termius Snippets
```
# Quick start
vibe $CLIPBOARD$

# Check status
vibe-list

# Git status
git status

# Run tests
npm test
```

### Keyboard Efficiency
- Use Claude Code's `/` commands instead of typing
- Tab completion is your friend
- `Ctrl+r` for command history search

### Battery & Data
- tmux sessions persist - disconnect freely
- Claude Code streams efficiently
- Enable Termius compression if on cellular

---

## Troubleshooting

### Can't connect?
```bash
# Check Lightsail firewall allows SSH (port 22)
# AWS Console > Lightsail > Instance > Networking
```

### Session disappeared?
```bash
# Sessions survive disconnects, but not reboots
# Check if tmux is running:
tmux list-sessions
```

### Claude not found?
```bash
# Reinstall Claude Code
npm install -g @anthropic-ai/claude-code

# Or check PATH
echo $PATH
```

### Out of memory?
```bash
# Check memory
free -h

# Consider upgrading Lightsail plan
# Or add swap:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Cost

| Lightsail Plan | RAM | Storage | Price |
|---------------|-----|---------|-------|
| Nano | 512MB | 20GB | $3.50/mo |
| Micro | 1GB | 40GB | $5/mo |
| Small | 2GB | 60GB | $10/mo |

**Recommendation**: Start with $5/mo plan. Upgrade if you run memory-heavy builds.

First 3 months are free on the first Lightsail instance!
