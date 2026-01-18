# Vibecoding Stack

Autonomous coding with quality gates and continuous learning.

**Autocoder + Planning Files + Aleph + Quality Gates + Learning**

## The Loop

```
┌─────────────────────────────────────────────────────────────────┐
│  1. GET FEATURE                                                 │
│     └─► feature_get_next → "Implement user auth"                │
├─────────────────────────────────────────────────────────────────┤
│  2. PLAN                                                        │
│     └─► feature_discuss → Surface unclear requirements          │
│     └─► Read task_plan.md, findings.md, progress.md             │
├─────────────────────────────────────────────────────────────────┤
│  3. EXPLORE                                                     │
│     └─► aleph_search → Find relevant code                       │
│     └─► aleph_peek → View specific files                        │
├─────────────────────────────────────────────────────────────────┤
│  4. IMPLEMENT                                                   │
│     └─► Write code following existing patterns                  │
│     └─► Write tests for all test cases                          │
├─────────────────────────────────────────────────────────────────┤
│  5. VERIFY                                                      │
│     └─► quality_check → lint, types, tests, build               │
│     └─► /verify → Full verification                             │
├─────────────────────────────────────────────────────────────────┤
│  6. COMPLETE                                                    │
│     └─► feature_mark_passing → Auto-runs quality gates          │
│     └─► /commit → Commit with good message                      │
├─────────────────────────────────────────────────────────────────┤
│  7. LEARN                                                       │
│     └─► /retrospective → Extract reusable knowledge             │
│     └─► Skills saved to ~/.claude/skills/learned/               │
├─────────────────────────────────────────────────────────────────┤
│  8. LOOP → Back to step 1                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: Lightsail + Mobile (Termius)

Code from your phone with persistent sessions.

```bash
# On your Lightsail instance
git clone https://github.com/StreetsDigital/vibes.git
cd vibes && ./lightsail/setup.sh

# Start coding
vibe my-project
claude
```

**4 tmux windows:** claude | shell | logs | scratch

👉 **[Full guide: lightsail/README.md](lightsail/README.md)**

---

### Option 2: GitHub Codespaces

Free cloud environment, no setup.

1. **Code** → **Codespaces** → **Create codespace**
2. Wait 2 minutes for auto-setup
3. Start coding:

```bash
vibecode new my-project python
vibecode code my-project
```

👉 **[Full guide: CODESPACES.md](CODESPACES.md)**

---

### Option 3: Local Setup

```bash
./vibecode init
./vibecode new my-api python
./vibecode code my-api
```

👉 **[Full guide: GETTING_STARTED.md](GETTING_STARTED.md)**

## Commands

### vibecode (Project Management)

```bash
vibecode init                      # Install ClaudeBox + dependencies
vibecode new <project> [profile]   # Create isolated environment
vibecode shell <project>           # Enter project shell
vibecode code <project>            # Start Claude Code
vibecode list                      # List all projects
vibecode status [project]          # Show project info
vibecode remove <project>          # Delete project
vibecode lightsail setup           # Install mobile environment
vibecode lightsail session [name]  # Start/attach tmux session
vibecode dashboard [port]          # Start web dashboard (default: 8080)
```

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/verify` | Run full quality verification |
| `/commit` | Quality check + commit + push |
| `/retrospective` | Extract learnings as reusable skills |

### MCP Tools

| Category | Tools |
|----------|-------|
| **Features** | `feature_get_next`, `feature_mark_passing`, `feature_skip` |
| **Planning** | `feature_discuss`, `feature_assumptions`, `feature_research` |
| **Search** | `aleph_search`, `aleph_peek`, `aleph_cite`, `aleph_refresh` |
| **Quality** | `quality_check`, `quality_verify` |
| **Subagent** | `subagent_spawn` |

## Structure

```
vibes/
├── vibecode                    # Main CLI tool
├── mcp_server/
│   ├── vibecoding_server.py    # Combined MCP server
│   ├── aleph_bridge.py         # Codebase search
│   ├── quality_gates.py        # Tests/lint/types
│   └── subagent_spawner.py     # Fresh context agents
├── .claude/
│   ├── settings.json           # Permissions + hooks
│   ├── commands/               # /verify, /commit, /retrospective
│   └── skills/
│       ├── continuous-learning/  # Learning framework
│       └── learned/              # Saved skills
├── lightsail/
│   ├── setup.sh                # Mobile setup script
│   └── README.md               # Termius guide
├── dashboard/
│   ├── server.py               # Web dashboard server
│   └── log-event.sh            # Event logging script
└── scripts/
    ├── init-session.sh         # Planning files setup
    ├── test-flow.sh            # Stack verification tests
    └── test-learning.sh        # Learning flow tests
```

## Continuous Learning

Sessions automatically evaluate for extractable knowledge:

```
Debug issue → Find solution → /retrospective → Save as skill → Future sessions apply it
```

Skills are saved as markdown with YAML frontmatter:

```markdown
---
name: fix-prisma-connections
description: Fix "Too many connections" in serverless
---

## Trigger
Error: "Too many connections" with Prisma

## Solution
1. Use singleton pattern
2. Set connection_limit in DATABASE_URL
```

## Quality Gates

Every feature must pass before completion:

| Check | Command |
|-------|---------|
| Tests | `npm test` / `pytest` |
| Lint | `npm run lint` / `ruff` |
| Types | `tsc --noEmit` / `mypy` |
| Build | `npm run build` |

```bash
# Quick check
quality_check(quick=True)

# Full check
quality_check()

# Mark complete (auto-runs gates)
feature_mark_passing(id)
```

## Activity Dashboard

Monitor all activity in real-time via web browser:

```bash
# Start dashboard
vibecode dashboard 8080

# Or directly
python3 dashboard/server.py 8080
```

Access at `http://localhost:8080` (or your Lightsail IP).

Features:
- Real-time activity log with auto-refresh
- Session/feature/commit statistics
- Learned skills viewer
- Dark theme, mobile-friendly

Logs stored in `~/.claude/logs/activity.jsonl`.

## Project Isolation

Each project gets:
- Own `.claude/settings.json`
- Separate MCP server instance
- Independent autocoder database
- Isolated Aleph codebase index
- Zero context bleed

## Planning Files

```
project/
├── task_plan.md    # Goals and phases
├── findings.md     # Technical discoveries
└── progress.md     # What's been done
```

Initialize with:
```bash
~/autocoder/scripts/init-session.sh
```

## Profiles

| Profile | Languages/Tools |
|---------|-----------------|
| `python` | Python 3.11, pip, pytest, ruff |
| `javascript` | Node 20, npm, TypeScript |
| `go` | Go 1.22, golangci-lint |
| `rust` | Rust, cargo, clippy |
| `java` | JDK 21, Maven, Gradle |
| `php` | PHP 8.3, Composer |
| `ruby` | Ruby 3.3, Bundler |
| `c` / `cpp` | GCC, CMake, Make |

## Related Docs

- [CLAUDE.md](CLAUDE.md) - Full workflow instructions
- [EXAMPLE_WORKFLOW.md](EXAMPLE_WORKFLOW.md) - Building UI for adtech-proton
- [CODESPACES.md](CODESPACES.md) - GitHub Codespaces setup
- [GETTING_STARTED.md](GETTING_STARTED.md) - Local installation
- [lightsail/README.md](lightsail/README.md) - Mobile coding with Termius
