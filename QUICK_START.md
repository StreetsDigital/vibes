# Quick Start - 3 Steps to Coding

## Step 1: Choose Your Environment

### ☁️ Cloud (GitHub Codespaces) - RECOMMENDED
**No Docker installation needed!**

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Setup vibecoding-stack"
git remote add origin https://github.com/YOUR-USERNAME/vibecoding-stack.git
git push -u origin master

# 2. Open Codespaces
# Go to: https://github.com/YOUR-USERNAME/vibecoding-stack
# Click: Code → Codespaces → Create codespace

# 3. Wait 2 minutes for auto-setup
# Done! Docker is already running in the cloud
```

See: [CODESPACES.md](CODESPACES.md)

---

### 💻 Local (Your Machine)
**Requires Docker Desktop**

```bash
# 1. Start Docker Desktop
open -a Docker

# 2. Initialize
./vibecode init
```

See: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## Step 2: Create Your First Project

```bash
# Python project
vibecode new my-api python

# JavaScript project
vibecode new my-frontend javascript

# Go project
vibecode new my-service go

# See all options
vibecode help
```

---

## Step 3: Start Coding

```bash
# Start Claude Code in isolated environment
vibecode code my-api
```

Inside Claude Code:
1. `feature_get_next` - Get next task
2. `aleph_search` - Search codebase
3. Write code + tests
4. `quality_check` - Verify quality
5. `feature_mark_passing` - Complete
6. `/commit` - Commit changes

---

## Common Commands

```bash
vibecode list              # Show all projects
vibecode status my-api     # Project details
vibecode shell my-api      # Enter shell
vibecode remove old-proj   # Delete project
```

---

## Switching Projects (Zero Bleed!)

```bash
# Morning: E-commerce
vibecode code ecommerce-api
# ... work ...
# Exit

# Afternoon: Payment service
vibecode code payment-service
# Fresh environment, different config!
```

---

## What You Get

✅ Complete project isolation
✅ Docker containers per project
✅ Different settings per project
✅ Separate MCP servers
✅ Independent databases
✅ Zero context bleed

---

## Next Steps

- **Full guide:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Cloud setup:** [CODESPACES.md](CODESPACES.md)
- **Workflow details:** [CLAUDE.md](CLAUDE.md)
- **Isolation explained:** [CLAUDEBOX_INTEGRATION.md](CLAUDEBOX_INTEGRATION.md)

---

**That's it! Pick cloud or local, create a project, start coding. 🚀**
