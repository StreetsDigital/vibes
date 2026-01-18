# Quick Start Guide

Get coding in 3 steps.

## Step 1: Clone & Setup

```bash
# On your Lightsail instance (or any Linux server)
git clone https://github.com/StreetsDigital/vibes.git
cd vibes

# Run interactive setup (configures AWS + OpenAI)
./vibecode setup
```

The setup wizard will prompt you for:
- **AWS credentials** (for auto-opening firewall ports)
- **OpenAI API key** (for `/codex-review` bug detection)

Don't have these yet? No problem - skip them and add later.

---

## Step 2: Start Coding

```bash
# Start a coding session
vibe my-project

# This creates 4 tmux windows:
# 1. claude  - Main Claude Code session
# 2. shell   - For running commands
# 3. logs    - For watching logs
# 4. scratch - For exploration
```

In the claude window:
```bash
claude
```

---

## Step 3: Use the Flow

Inside Claude Code, the workflow is:

```
1. feature_get_next       → Get next task from queue
2. aleph_search           → Find relevant code
3. [Write code + tests]
4. quality_check          → Verify lint/types/tests pass
5. feature_mark_passing   → Mark complete
6. /commit                → Commit with good message
7. /codex-review          → AI bug detection (optional)
8. /retrospective         → Extract learnings (after debugging)
```

---

## Key Commands

### vibecode CLI

| Command | What it does |
|---------|--------------|
| `vibecode setup` | Interactive credential setup |
| `vibecode dashboard 8498` | Start web dashboard |
| `vibecode lightsail open-port 3000` | Open firewall port |
| `vibecode help` | Show all commands |

### Slash Commands (inside Claude)

| Command | What it does |
|---------|--------------|
| `/verify` | Run full quality verification |
| `/commit` | Quality check + commit + push |
| `/codex-review` | Send code to OpenAI for bug analysis |
| `/retrospective` | Extract learnings as reusable skills |

### tmux Navigation

| Keys | Action |
|------|--------|
| `Ctrl+a 1` | Go to claude window |
| `Ctrl+a 2` | Go to shell window |
| `Ctrl+a 3` | Go to logs window |
| `Ctrl+a 4` | Go to scratch window |
| `Ctrl+a d` | Detach (keeps session running) |

---

## Credentials Setup

If you skipped setup, add credentials anytime:

```bash
# Re-run interactive setup
./vibecode setup

# Or manually:

# AWS (for port management)
mkdir -p ~/.aws
cat > ~/.aws/credentials << 'EOF'
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
EOF
cat > ~/.aws/config << 'EOF'
[default]
region = eu-west-1
EOF

# OpenAI (for /codex-review)
mkdir -p ~/.config/openai
echo "sk-your-api-key" > ~/.config/openai/api_key
```

---

## Web Dashboard

Monitor activity in your browser:

```bash
./vibecode dashboard 8498
```

Opens `http://YOUR-IP:8498` automatically (if AWS configured).

Features:
- Real-time activity log
- Session statistics
- Learned skills viewer

---

## The Full Loop

```
┌─────────────────────────────────────────────────────────────────┐
│  1. GET FEATURE     → feature_get_next                          │
│  2. PLAN            → feature_discuss, read task_plan.md        │
│  3. EXPLORE         → aleph_search, aleph_peek                  │
│  4. IMPLEMENT       → Write code + tests                        │
│  5. VERIFY          → quality_check, /verify                    │
│  6. COMPLETE        → feature_mark_passing, /commit             │
│  7. LEARN           → /retrospective (after debugging)          │
│  8. LOOP            → Back to step 1                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

- **Full workflow details:** [CLAUDE.md](CLAUDE.md)
- **Lightsail setup:** [lightsail/README.md](lightsail/README.md)
- **Project isolation:** [CLAUDEBOX_INTEGRATION.md](CLAUDEBOX_INTEGRATION.md)

---

**Questions?** Just ask Claude - it knows the system.
