# Getting Started with Vibecode

**One script. Infinite isolated projects. Zero bleed.**

---

## Installation (One Command)

```bash
cd vibecoding-stack
./vibecode init
```

This installs:
- ✅ ClaudeBox (Docker-based isolation)
- ✅ Python dependencies (SQLAlchemy, MCP, Aleph)
- ✅ Global `vibecode` command

**Done!** You're ready to create isolated environments.

---

## Create Your First Project

```bash
# E-commerce API (Python)
vibecode new ecommerce-api python

# React frontend (JavaScript)
vibecode new ecommerce-frontend javascript

# Go microservice
vibecode new payment-service go
```

Each project is **completely isolated**:
- Separate Docker container
- Independent `.claude/settings.json`
- Isolated MCP server
- Dedicated autocoder database
- Project-specific Aleph index

---

## Start Coding

### Option 1: Interactive Shell

```bash
vibecode shell ecommerce-api
# Now inside isolated container
cd /workspace
claude
```

### Option 2: Direct Launch

```bash
vibecode code ecommerce-api
# Claude Code starts directly
```

---

## Daily Workflow

### Morning: E-commerce API

```bash
vibecode code ecommerce-api
```

Inside Claude Code:
1. `feature_get_next` → Get next feature
2. `feature_discuss` → Plan approach
3. `aleph_search` → Find relevant code
4. Write code + tests
5. `quality_check` → Verify
6. `feature_mark_passing` → Complete
7. Commit with `/commit`

**Exit Claude Code**

---

### Afternoon: Payment Service

```bash
vibecode code payment-service
# Completely fresh environment!
# Different config, different context
# ZERO bleed from ecommerce-api
```

Same workflow, but:
- Different `.claude/settings.json` (maybe stricter permissions)
- Different MCP server instance
- Different autocoder features
- Different Aleph index

**No interference whatsoever!**

---

## Managing Projects

### List All Projects

```bash
vibecode list
```

Output:
```
  ecommerce-api
    Status: ✓ vibecoding
    Size:   1.2G
    Path:   ~/claudebox/ecommerce-api

  ecommerce-frontend
    Status: ✓ vibecoding
    Size:   890M
    Path:   ~/claudebox/ecommerce-frontend

  payment-service
    Status: ✓ vibecoding
    Size:   650M
    Path:   ~/claudebox/payment-service
```

### Check Project Status

```bash
vibecode status ecommerce-api
```

Output:
```
Project: ecommerce-api

Components:
  ✓ Autocoder
  ✓ MCP Server
  ✓ Claude Config

Storage:
  Total: 1.2G

Actions:
  vibecode shell ecommerce-api   - Enter shell
  vibecode code ecommerce-api    - Start Claude Code
```

### Remove Project

```bash
vibecode remove old-prototype
# Deletes entire container
# Frees up disk space
```

---

## Configuration per Project

Each project can have **different settings**:

### E-commerce API (`ecommerce-api/.claude/settings.json`)

```json
{
  "model": "claude-sonnet-4-20250514",
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Bash(pytest:*)",
      "Bash(pip install:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Read(.env*)"
    ]
  }
}
```

### Payment Service (`payment-service/.claude/settings.json`)

```json
{
  "model": "claude-opus-4-20250514",
  "permissions": {
    "allow": [
      "Bash(go:*)",
      "Bash(go test:*)"
    ],
    "deny": [
      "Bash(rm:*)",
      "Bash(*DROP*)",
      "Read(*secret*)"
    ]
  }
}
```

Different models, different permissions, **zero conflict!**

---

## Features

### Vibecoding Stack (in each project)

| Tool | Purpose |
|------|---------|
| **Autocoder** | Feature queue with SQLite |
| **Planning-with-Files** | `task_plan.md`, `findings.md`, `progress.md` |
| **Aleph** | Codebase search and indexing |
| **Quality Gates** | Tests, lint, types, security |

### MCP Tools (isolated per project)

```
feature_get_next        - Get next feature
feature_mark_passing    - Mark complete
feature_discuss         - Pre-planning
aleph_search           - Search code
aleph_peek             - View file
quality_check          - Run gates
```

---

## Advanced Usage

### Simultaneous Projects

Run multiple Claude Code instances in parallel:

```bash
# Terminal 1
vibecode code ecommerce-api

# Terminal 2
vibecode code payment-service

# Terminal 3
vibecode code ecommerce-frontend

# All isolated, no bleed!
```

### Custom Language Profiles

```bash
vibecode new rust-project rust
vibecode new java-service java
vibecode new php-api php
vibecode new cpp-engine cpp
```

Available profiles:
- `python` - Python + pip + venv
- `javascript` - Node.js + npm
- `go` - Go toolchain
- `rust` - Rust + Cargo
- `java` - JDK + Maven
- `php` - PHP + Composer
- `ruby` - Ruby + Bundler
- `c` / `cpp` - GCC + build tools

---

## Troubleshooting

### "claudebox not found"

```bash
./vibecode init
# Installs claudebox automatically
```

### "Project not found"

```bash
vibecode list
# Check project name spelling
```

### "MCP server not responding"

```bash
vibecode shell myproject
cd /workspace/autocoder/mcp_server
python3 vibecoding_server.py
# Check for errors
```

### Clean Slate

```bash
vibecode remove myproject
vibecode new myproject python
# Fresh start
```

---

## Migration from Shared Setup

### Before (Shared Everything)

```
~/.claude/settings.json          # Affects ALL projects
~/autocoder/features.db          # Mixed features
~/.config/claude-desktop/...     # Global config
```

**Problem:** Project A settings affect Project B!

### After (Isolated Everything)

```
~/claudebox/project-a/
  ├── .claude/settings.json      # Project A only
  └── autocoder/features.db      # Project A only

~/claudebox/project-b/
  ├── .claude/settings.json      # Project B only
  └── autocoder/features.db      # Project B only
```

**Solution:** Complete isolation!

### Migration Steps

1. **List current projects**: What are you working on?
2. **Create containers**: `vibecode new` for each
3. **Copy code**: Move project files to `/workspace`
4. **Test**: Verify isolation with `vibecode code <project>`
5. **Archive old setup**: Backup shared config

---

## Best Practices

1. **One project = One container**: Don't share
2. **Descriptive names**: `ecommerce-api` not `test`
3. **Regular cleanup**: Remove old prototypes
4. **Backup features.db**: Before removing containers
5. **Version control settings**: Commit `.claude/settings.json`

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Setup | Multiple scripts | `./vibecode init` |
| New project | Manual config | `vibecode new` |
| Start coding | Find directory | `vibecode code` |
| Bleed | ❌ Yes | ✅ No |
| Isolation | ❌ None | ✅ Complete |
| Switching | ❌ Hard | ✅ Instant |

**One script. Total control. Zero bleed.**

---

## Next Steps

1. Initialize: `./vibecode init`
2. Create project: `vibecode new myproject python`
3. Start coding: `vibecode code myproject`
4. Read: `CLAUDE.md` for workflow details

**Welcome to isolated autonomous coding!** 🎉
