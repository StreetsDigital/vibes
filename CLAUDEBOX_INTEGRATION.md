# ClaudeBox + Vibecoding Stack Integration

Eliminate project bleed by running each project in its own isolated ClaudeBox container with dedicated vibecoding-stack configuration.

## The Problem

Without containerization:
- `.claude/settings.json` shared across all projects
- MCP server state bleeds between sessions
- Context from Project A affects Project B
- Hard to maintain different configurations per project

## The Solution

ClaudeBox provides Docker-based isolation where each project gets:
- ✅ Its own `.claude/` configuration directory
- ✅ Isolated MCP server instance
- ✅ Separate autocoder database
- ✅ Independent Aleph index
- ✅ Project-specific quality gates

---

## Quick Start

### 1. Install ClaudeBox

```bash
wget https://github.com/RchGrav/claudebox/releases/latest/download/claudebox.run
chmod +x claudebox.run
./claudebox.run
```

### 2. Create Project-Specific Containers

For each project, create an isolated environment:

```bash
# Project 1: E-commerce site
claudebox new ecommerce --profile python
cd ~/claudebox/ecommerce
# Install vibecoding-stack inside this container
git clone <your-vibecoding-stack-repo> .vibecoding
.vibecoding/setup.sh

# Project 2: ML Pipeline
claudebox new ml-pipeline --profile python
cd ~/claudebox/ml-pipeline
git clone <your-vibecoding-stack-repo> .vibecoding
.vibecoding/setup.sh

# Each project now has:
# - Separate .claude/settings.json
# - Isolated MCP server
# - Independent autocoder database
```

### 3. Start Claude Code in Container

```bash
# Enter the container
claudebox shell ecommerce

# Start Claude Code
cd /workspace/your-project
claude

# Your vibecoding-stack is now scoped to THIS project only
```

---

## Custom Vibecoding Profile (Advanced)

Create a reusable ClaudeBox profile with vibecoding pre-installed:

### 1. Build Custom Image

```bash
cd /path/to/vibecoding-stack
docker build -f Dockerfile.claudebox -t claudebox-vibecoding .
```

### 2. Use Custom Image

```bash
# Create new project with vibecoding pre-installed
claudebox new myproject --image claudebox-vibecoding

# Everything is already configured!
```

---

## Per-Project Configuration

Each ClaudeBox container maintains its own:

### Directory Structure
```
~/claudebox/
├── project-a/
│   ├── .claude/
│   │   ├── settings.json          # Project A config
│   │   └── commands/
│   ├── autocoder/
│   │   └── features.db            # Project A features
│   └── .aleph/                    # Project A index
│
├── project-b/
│   ├── .claude/
│   │   ├── settings.json          # Project B config (different!)
│   │   └── commands/
│   ├── autocoder/
│   │   └── features.db            # Project B features
│   └── .aleph/                    # Project B index
```

### Settings Isolation

**Project A** `.claude/settings.json`:
```json
{
  "model": "claude-sonnet-4-20250514",
  "permissions": {
    "allow": ["Bash(npm:*)"],
    "deny": ["Bash(rm -rf:*)"]
  }
}
```

**Project B** `.claude/settings.json`:
```json
{
  "model": "claude-opus-4-20250514",
  "permissions": {
    "allow": ["Bash(python:*)", "Bash(pytest:*)"],
    "deny": ["Bash(pip install:*)"]
  }
}
```

No interference between projects!

---

## Workflow

### Daily Usage

```bash
# Morning: Work on E-commerce
claudebox shell ecommerce
cd /workspace
claude
# Feature development with vibecoding...
exit

# Afternoon: Switch to ML Pipeline
claudebox shell ml-pipeline
cd /workspace
claude
# Completely fresh context, different config
```

### Benefits

1. **No Context Bleed**: Each container is isolated
2. **Different Configs**: Customize per project
3. **Clean State**: Stop/start containers as needed
4. **Reproducible**: Share container setup with team
5. **Security**: Different permission profiles per project

---

## Troubleshooting

### Issue: MCP Server Not Found

```bash
# Inside container
echo $PATH
# Ensure Python and pip are in PATH

# Reinstall vibecoding
cd .vibecoding && ./setup.sh
```

### Issue: Settings Not Applied

```bash
# Check settings location
ls -la /workspace/.claude/settings.json

# Restart Claude Code to pick up changes
```

### Issue: Container Can't Access Host Files

```bash
# Mount additional volumes when creating container
claudebox new myproject --volume ~/Documents:/docs
```

---

## Best Practices

1. **One Container Per Major Project**: Don't share containers
2. **Commit Container State**: Use Docker commits for reproducibility
3. **Backup Autocoder DB**: `~/claudebox/<project>/autocoder/features.db`
4. **Version Control Settings**: Add `.claude/settings.json` to git
5. **Use Profiles**: Create custom profiles for common stacks

---

## Migration from Shared Setup

### Before (Bleeding)
```
~/.claude/settings.json              # ❌ Shared across all projects
~/autocoder/features.db              # ❌ Mixed features
~/.config/claude-desktop/config.json # ❌ Global MCP config
```

### After (Isolated)
```
~/claudebox/project-a/.claude/        # ✅ Project A only
~/claudebox/project-b/.claude/        # ✅ Project B only
~/claudebox/project-c/.claude/        # ✅ Project C only
```

### Migration Steps

1. **List Current Projects**: Identify what you're working on
2. **Create Containers**: One claudebox per project
3. **Copy Configs**: Move project-specific settings to each container
4. **Test Isolation**: Verify no bleed between containers
5. **Archive Old Setup**: Keep backup of shared config

---

## Advanced: Multi-Instance Claude

Run Claude Code in multiple containers simultaneously:

```bash
# Terminal 1: E-commerce
claudebox shell ecommerce
claude --port 3001

# Terminal 2: ML Pipeline
claudebox shell ml-pipeline
claude --port 3002

# Each has separate MCP servers, configs, state
```

---

## Summary

| Aspect | Without ClaudeBox | With ClaudeBox |
|--------|------------------|----------------|
| Config | Shared `.claude/settings.json` | Per-container |
| MCP State | Global, bleeds between projects | Isolated |
| Autocoder DB | Single `features.db` | One per project |
| Aleph Index | Shared index | Per-project index |
| Switching Cost | High (context bleed) | Low (clean slate) |

ClaudeBox + Vibecoding Stack = **True Project Isolation** 🎉
