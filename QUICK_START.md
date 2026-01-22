# Quick Start Guide

Get coding in 3 steps.

## Step 1: Clone & Install

```bash
# On your server
git clone https://github.com/StreetsDigital/vibes.git
cd vibes

# Install everything
./vibecode install --server
```

The installer sets up:
- Docker & dependencies
- Claude Code CLI
- MCP servers (vibecoding, atom-of-thoughts, sequential-thinking)
- Quality gates & pre-commit hooks

---

## Step 2: Start Coding

```bash
# Switch to vibes user
su - vibes

# Start Claude in the autocoder directory
cd ~/autocoder
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
| `vibecode install --server` | Full server installation |
| `vibecode setup` | Configure OpenAI API key |
| `vibecode dashboard 8080` | Start web dashboard |
| `vibecode help` | Show all commands |

### Slash Commands (inside Claude)

| Command | What it does |
|---------|--------------|
| `/verify` | Run full quality verification |
| `/commit` | Quality check + commit + push |
| `/codex-review` | Send code to OpenAI for bug analysis |
| `/retrospective` | Extract learnings as reusable skills |

---

## Optional: OpenAI Setup

For `/codex-review` bug detection:

```bash
./vibecode setup

# Or manually:
mkdir -p ~/.config/openai
echo "sk-your-api-key" > ~/.config/openai/api_key
```

---

## Web Dashboard

Monitor activity in your browser:

```bash
./vibecode dashboard 8080
```

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
- **Project isolation:** [CLAUDEBOX_INTEGRATION.md](CLAUDEBOX_INTEGRATION.md)

---

**Questions?** Just ask Claude - it knows the system.
