#!/bin/bash
#
# GitHub Codespaces Auto-Setup for Vibecoding Stack
# ==================================================
# Runs automatically when Codespace is created
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     VIBECODING STACK - CODESPACE SETUP                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Wait for Docker to be ready
echo -e "${BLUE}==> Waiting for Docker...${NC}"
timeout=30
while ! docker info >/dev/null 2>&1; do
    if [ $timeout -le 0 ]; then
        echo -e "${YELLOW}⚠ Docker not ready, continuing anyway...${NC}"
        break
    fi
    sleep 1
    timeout=$((timeout - 1))
done

if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker is ready${NC}"
else
    echo -e "${YELLOW}⚠ Docker not available yet (may need to wait)${NC}"
fi

# Make vibecode executable
echo -e "${BLUE}==> Setting up vibecode command...${NC}"
chmod +x /workspaces/vibecoding-stack/vibecode

# Add to PATH
echo 'export PATH="/workspaces/vibecoding-stack:$PATH"' >> ~/.bashrc

# Install Python dependencies
echo -e "${BLUE}==> Installing Python dependencies...${NC}"
pip install --user --quiet sqlalchemy mcp 2>/dev/null || true

# Try to install Aleph
pip install --user --quiet "aleph-rlm[mcp]" 2>/dev/null || \
    pip install --user --quiet "git+https://github.com/Hmbown/aleph.git#egg=aleph-rlm[mcp]" 2>/dev/null || \
    echo -e "${YELLOW}⚠ Aleph installation skipped${NC}"

# Install ClaudeBox (if Docker is ready)
if docker info >/dev/null 2>&1; then
    echo -e "${BLUE}==> Installing ClaudeBox...${NC}"

    INSTALLER="/tmp/claudebox.run"
    URL="https://github.com/RchGrav/claudebox/releases/latest/download/claudebox.run"

    curl -fsSL "$URL" -o "$INSTALLER"
    chmod +x "$INSTALLER"
    "$INSTALLER" || echo -e "${YELLOW}⚠ ClaudeBox installation had warnings${NC}"

    echo -e "${GREEN}✓ ClaudeBox installed${NC}"
else
    echo -e "${YELLOW}⚠ Skipping ClaudeBox (Docker not ready)${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     SETUP COMPLETE!                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Quick Start:"
echo ""
echo "  ${GREEN}vibecode new my-first-project python${NC}"
echo "  ${GREEN}vibecode code my-first-project${NC}"
echo ""
echo "Commands:"
echo "  ${BLUE}vibecode list${NC}      - List all projects"
echo "  ${BLUE}vibecode status${NC}    - Show project status"
echo "  ${BLUE}vibecode help${NC}      - Show all commands"
echo ""
echo "Read: ${BLUE}GETTING_STARTED.md${NC} for full guide"
echo ""
