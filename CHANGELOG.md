# Changelog

## 2026-01-18 - Project Isolation Update

### Fixed Issues

1. **`.claude/settings.json` validation errors** (3 issues)
   - Fixed $schema URL to use official `https://json.schemastore.org/claude-code-settings.json`
   - Changed `model` from object to string: `"claude-sonnet-4-20250514"`
   - Fixed permission patterns:
     - `Bash(wget:*|sh)` → `Bash(wget * | sh)`
     - `Bash(curl:*|sh)` → `Bash(curl * | sh)`

2. **README hardcoded path**
   - Changed `~/Desktop/vibecoding-stack/` to `/absolute/path/to/vibecoding-stack/`
   - Added note for users to customize path

### New Features

#### 🎯 **ClaudeBox Integration** - Complete Project Isolation

Added full support for running isolated vibecoding environments using ClaudeBox:

**New Files:**
- `vibecode` - **Unified management script (ONE COMMAND FOR EVERYTHING)**
- `CLAUDEBOX_INTEGRATION.md` - Detailed integration guide
- `GETTING_STARTED.md` - Complete walkthrough
- `Dockerfile.claudebox` - Custom ClaudeBox profile
- `claudebox-create.sh` - Helper script for creating isolated environments

**Benefits:**
- ✅ **Zero project bleed** - Each project in its own Docker container
- ✅ **Isolated configs** - Separate `.claude/settings.json` per project
- ✅ **Independent MCP servers** - No shared state
- ✅ **Project-specific databases** - Isolated autocoder features
- ✅ **Clean context switching** - No contamination between projects

#### 📦 **The `vibecode` Command**

One script to manage everything:

```bash
vibecode init                    # Install ClaudeBox + dependencies
vibecode new <project> [profile] # Create isolated environment
vibecode shell <project>         # Enter project shell
vibecode code <project>          # Start Claude Code
vibecode list                    # List all projects
vibecode status [project]        # Show project info
vibecode remove <project>        # Delete project
```

**Example Workflow:**

```bash
# First time setup
./vibecode init

# Create isolated projects
vibecode new ecommerce-api python
vibecode new payment-service go
vibecode new admin-frontend javascript

# Start coding (completely isolated)
vibecode code ecommerce-api

# Switch projects (zero bleed)
vibecode code payment-service

# Manage projects
vibecode list
vibecode status ecommerce-api
vibecode remove old-prototype
```

### Technical Details

#### Architecture

**Before:**
```
~/.claude/settings.json        # Shared across ALL projects ❌
~/autocoder/features.db        # Mixed features from all projects ❌
~/.config/claude-desktop/...   # Global MCP configuration ❌
```

**After:**
```
~/claudebox/project-a/
  ├── .claude/settings.json       # Project A only ✅
  ├── autocoder/features.db       # Project A only ✅
  └── .config/claude-desktop/...  # Project A only ✅

~/claudebox/project-b/
  ├── .claude/settings.json       # Project B only ✅
  ├── autocoder/features.db       # Project B only ✅
  └── .config/claude-desktop/...  # Project B only ✅
```

#### What Gets Isolated

Each container has its own:
1. **Claude Code settings** - Different models, permissions, behavior
2. **MCP server instances** - No shared state
3. **Autocoder database** - Independent feature queues
4. **Aleph index** - Project-specific codebase search
5. **Quality gates config** - Custom gates per project
6. **Git configuration** - Separate identities if needed
7. **Environment variables** - Project-specific secrets

### Use Cases

This update enables:

1. **Multi-project developers** - Work on 5+ projects without bleed
2. **Different tech stacks** - Python project, Go project, JS project simultaneously
3. **Client work** - Isolated environments per client
4. **Experimentation** - Spin up throwaway environments
5. **Team collaboration** - Share container configs
6. **CI/CD testing** - Reproducible environments

### Migration Path

For existing users:

1. Run `./vibecode init` to set up ClaudeBox
2. Create new isolated projects with `vibecode new`
3. Move existing code into containers
4. Archive old shared setup
5. Enjoy zero-bleed development

### Documentation

- `README.md` - Updated with quick start
- `GETTING_STARTED.md` - Comprehensive guide
- `CLAUDEBOX_INTEGRATION.md` - Deep dive on isolation
- `CLAUDE.md` - Workflow instructions (unchanged)

### Breaking Changes

None! The original `setup.sh` still works for single-project setups. The `vibecode` script adds optional containerization.

### Next Steps

Future enhancements:
- [ ] Pre-built Docker images for faster startup
- [ ] Cloud sync for container configs
- [ ] VS Code integration
- [ ] Team collaboration features
- [ ] Container templates for common stacks

---

**Summary:** This update solves the "project bleed" problem by containerizing each project with ClaudeBox, managed through a single `vibecode` command. Each project gets complete isolation while maintaining the full vibecoding stack functionality.
