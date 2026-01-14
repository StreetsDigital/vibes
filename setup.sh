#!/usr/bin/env bash
#
# Vibecoding Stack Setup Script
# =============================
# 
# Installs and configures the three-layer autonomous coding stack:
# 1. Autocoder - Session orchestration
# 2. Planning-with-Files - Goal coherence  
# 3. Aleph - Context management
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOCODER_DIR="${AUTOCODER_DIR:-$HOME/autocoder}"
PLANNING_DIR="${PLANNING_DIR:-$HOME/.claude/skills/planning-with-files}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${BLUE}==>${NC} $1"
}

echo_success() {
    echo -e "${GREEN}✓${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo_error() {
    echo -e "${RED}✗${NC} $1"
}

# =============================================================================
# CHECKS
# =============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           VIBECODING STACK INSTALLER                         ║"
echo "║                                                              ║"
echo "║  Autocoder + Planning-with-Files + Aleph                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo_step "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo_success "Python found: $PYTHON_VERSION"
else
    echo_error "Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Check pip
echo_step "Checking pip..."
if command -v pip3 &> /dev/null; then
    echo_success "pip found"
else
    echo_error "pip3 not found"
    exit 1
fi

# Check Claude CLI
echo_step "Checking Claude CLI..."
if command -v claude &> /dev/null; then
    echo_success "Claude CLI found"
else
    echo_warning "Claude CLI not found"
    echo "  Install with: curl -fsSL https://claude.ai/install.sh | bash"
    echo "  Continuing anyway..."
fi

# Check git
echo_step "Checking git..."
if command -v git &> /dev/null; then
    echo_success "git found"
else
    echo_error "git not found"
    exit 1
fi

# =============================================================================
# INSTALL DEPENDENCIES
# =============================================================================

echo ""
echo_step "Installing Python dependencies..."

# Core dependencies
pip3 install --user --break-system-packages --quiet sqlalchemy

# Aleph
echo_step "Installing Aleph RLM..."
pip3 install --user --break-system-packages --quiet aleph-rlm[mcp] || {
    echo_warning "Could not install aleph-rlm from PyPI"
    echo "  Trying from GitHub..."
    pip3 install --user --break-system-packages --quiet "git+https://github.com/Hmbown/aleph.git#egg=aleph-rlm[mcp]" || {
        echo_warning "Could not install Aleph. Some features will be disabled."
    }
}

# MCP SDK
pip3 install --user --break-system-packages --quiet mcp || echo_warning "MCP SDK not installed"

echo_success "Dependencies installed"

# =============================================================================
# CLONE REPOSITORIES
# =============================================================================

echo ""
echo_step "Setting up repositories..."

# Autocoder
if [ -d "$AUTOCODER_DIR" ]; then
    echo_success "Autocoder already exists at $AUTOCODER_DIR"
else
    echo_step "Cloning autocoder..."
    git clone https://github.com/leonvanzyl/autocoder.git "$AUTOCODER_DIR"
    echo_success "Autocoder cloned"
fi

# Planning-with-files (as Claude skill)
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"

if [ -d "$PLANNING_DIR" ]; then
    echo_success "Planning-with-files already exists"
else
    echo_step "Installing planning-with-files skill..."
    git clone https://github.com/OthmanAdi/planning-with-files.git /tmp/planning-with-files
    cp -r /tmp/planning-with-files/planning-with-files "$PLANNING_DIR"
    rm -rf /tmp/planning-with-files
    echo_success "Planning-with-files installed as Claude skill"
fi

# =============================================================================
# INTEGRATE ALEPH BRIDGE & SUBAGENT SPAWNER
# =============================================================================

echo ""
echo_step "Integrating Aleph bridge and subagent spawner into autocoder..."

# Copy our integration files
mkdir -p "$AUTOCODER_DIR/mcp_server"
cp "$SCRIPT_DIR/aleph_bridge.py" "$AUTOCODER_DIR/mcp_server/"
cp "$SCRIPT_DIR/subagent_spawner.py" "$AUTOCODER_DIR/mcp_server/"
cp "$SCRIPT_DIR/feature_mcp_integrated.py" "$AUTOCODER_DIR/mcp_server/"

# Copy CLAUDE.md
cp "$SCRIPT_DIR/CLAUDE.md" "$AUTOCODER_DIR/"

# Copy init-session script
mkdir -p "$AUTOCODER_DIR/scripts"
cp "$SCRIPT_DIR/init-session.sh" "$AUTOCODER_DIR/scripts/"

echo_success "Integration files copied"

# =============================================================================
# CONFIGURE ALEPH
# =============================================================================

echo ""
echo_step "Configuring Aleph..."

# Run Aleph installer if available
if command -v aleph-rlm &> /dev/null; then
    echo_step "Running Aleph auto-installer..."
    aleph-rlm install || echo_warning "Aleph auto-install skipped"
else
    echo_warning "aleph-rlm command not found, manual config needed"
fi

# Create/update Claude Desktop config
CLAUDE_CONFIG_DIR="$HOME/.config/claude-desktop"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

mkdir -p "$CLAUDE_CONFIG_DIR"

if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo_step "Updating Claude Desktop config..."
    # Backup existing
    cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.bak"
    
    # Add our MCP server (using jq if available, otherwise manual)
    if command -v jq &> /dev/null; then
        # Add vibecoding MCP server
        jq '.mcpServers.vibecoding = {"command": "python3", "args": ["'"$AUTOCODER_DIR"'/mcp_server/feature_mcp_integrated.py"]}' \
            "$CLAUDE_CONFIG_FILE" > "$CLAUDE_CONFIG_FILE.tmp" && \
            mv "$CLAUDE_CONFIG_FILE.tmp" "$CLAUDE_CONFIG_FILE"
        # Add Context7 MCP server for up-to-date docs
        jq '.mcpServers.context7 = {"command": "npx", "args": ["-y", "@upstash/context7-mcp@latest"]}' \
            "$CLAUDE_CONFIG_FILE" > "$CLAUDE_CONFIG_FILE.tmp" && \
            mv "$CLAUDE_CONFIG_FILE.tmp" "$CLAUDE_CONFIG_FILE"
        echo_success "Updated Claude Desktop config (vibecoding + Context7)"
    else
        echo_warning "jq not found, please manually add MCP server config"
    fi
else
    # Create new config with both servers
    cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "vibecoding": {
      "command": "python3",
      "args": ["$AUTOCODER_DIR/mcp_server/feature_mcp_integrated.py"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
EOF
    echo_success "Created Claude Desktop config (vibecoding + Context7)"
fi

# =============================================================================
# VERIFY INSTALLATION
# =============================================================================

echo ""
echo_step "Verifying installation..."

# Check Aleph
python3 -c "import aleph; print('Aleph version:', aleph.__version__)" 2>/dev/null && \
    echo_success "Aleph import OK" || \
    echo_warning "Aleph import failed"

# Check bridge
python3 -c "from mcp_server.aleph_bridge import get_aleph_tools; print('Tools:', len(get_aleph_tools()))" \
    --path "$AUTOCODER_DIR" 2>/dev/null && \
    echo_success "Aleph bridge OK" || \
    echo_warning "Aleph bridge import failed (may be path issue)"

# Check planning files skill
if [ -f "$PLANNING_DIR/SKILL.md" ]; then
    echo_success "Planning-with-files skill OK"
else
    echo_warning "Planning-with-files SKILL.md not found"
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           INSTALLATION COMPLETE                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Autocoder:            $AUTOCODER_DIR"
echo "  Planning skill:       $PLANNING_DIR"
echo "  CLAUDE.md:            $AUTOCODER_DIR/CLAUDE.md"
echo ""
echo "  To start a project:"
echo ""
echo "    cd $AUTOCODER_DIR"
echo "    ./start.sh"
echo ""
echo "  Or with the Web UI:"
echo ""
echo "    ./start_ui.sh"
echo ""
echo "  The vibecoding stack will:"
echo "    1. Autocoder manages features in SQLite"
echo "    2. Planning files keep goals in attention"
echo "    3. Aleph indexes codebase for efficient search"
echo ""
echo "  See CLAUDE.md for detailed usage instructions."
echo ""
