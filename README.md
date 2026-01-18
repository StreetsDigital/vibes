# Vibecoding Stack

Autonomous coding with quality gates: Autocoder + Planning Files + Aleph + Quality Gates

**✨ Isolated per-project environments with zero bleed**

## Quick Start

### 🚀 Option 1: GitHub Codespaces (Recommended - No Docker needed!)

**FREE cloud environment with Docker pre-installed:**

1. Push this repo to GitHub
2. Click: **Code** → **Codespaces** → **Create codespace**
3. Wait 2 minutes for auto-setup
4. Start coding!

```bash
vibecode new my-project python
vibecode code my-project
```

👉 **[Full Codespaces guide: CODESPACES.md](CODESPACES.md)**

---

### 💻 Option 2: Local Setup

```bash
# One command to manage everything
./vibecode init

# Create isolated project environments
./vibecode new my-api python
./vibecode new my-frontend javascript

# Start coding (completely isolated)
./vibecode code my-api
```

👉 **[Read the full guide: GETTING_STARTED.md](GETTING_STARTED.md)**

## Structure

```
mcp_server/
├── vibecoding_server.py   # Combined MCP server
├── aleph_bridge.py        # Codebase search
├── subagent_spawner.py    # Fresh context
└── quality_gates.py       # Tests/lint/types

.claude/
├── settings.json          # Permissions
└── commands/              # /verify, /commit
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "vibecoding": {
      "command": "python3",
      "args": ["/absolute/path/to/vibecoding-stack/mcp_server/vibecoding_server.py", "."]
    }
  }
}
```

**Note:** Replace `/absolute/path/to/vibecoding-stack/` with the actual path to this directory.

## All Commands (One Script)

```bash
vibecode init                    # Install everything
vibecode new <project> [profile] # Create isolated environment
vibecode shell <project>         # Enter project shell
vibecode code <project>          # Start Claude Code
vibecode list                    # List all projects
vibecode status [project]        # Show project info
vibecode remove <project>        # Delete project
```

## Why Isolation?

**Without isolation (❌ bleed):**
- Settings from Project A affect Project B
- MCP server state shared across all projects
- Context contamination between sessions

**With isolation (✅ clean):**
- Each project has its own `.claude/settings.json`
- Separate MCP server instances
- Independent autocoder databases
- Zero context bleed

## The Loop

1. `feature_get_next` → Get feature
2. `feature_discuss` → Think first
3. `aleph_search` → Find code
4. Implement → Write code + tests
5. `quality_check` → Verify
6. `feature_mark_passing` → Complete
7. Repeat

## Tools

| Category | Tools |
|----------|-------|
| Features | `feature_get_next`, `feature_mark_passing`, `feature_skip` |
| Planning | `feature_discuss`, `feature_assumptions`, `feature_research` |
| Search | `aleph_search`, `aleph_peek`, `aleph_cite`, `aleph_refresh` |
| Subagent | `subagent_spawn` |
| Quality | `quality_check`, `quality_verify` |
