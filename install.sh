#!/usr/bin/env bash
#
# Unified Vibes Stack Installer
# =============================
#
# Installs the complete enhanced autonomous coding stack:
# - Autocoder (Session orchestration)
# - Planning-with-Files (Goal coherence)
# - Aleph (Context management)
# - Enhanced UI with agent monitoring
# - Cognitive processing capabilities
# - Quality gates integration
#
# Usage:
#   ./install.sh                    # Local development setup
#   ./install.sh --server           # Full server deployment
#   ./install.sh --server --domain  # Server with custom domain
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOCODER_DIR="${AUTOCODER_DIR:-$HOME/autocoder}"
PLANNING_DIR="${PLANNING_DIR:-$HOME/.claude/skills/planning-with-files}"

# Configuration
SERVER_MODE=false
VIBES_USER="vibes"
VIBES_HOME="/home/${VIBES_USER}"
PROJECTS_DIR="${VIBES_HOME}/projects"
DOMAIN=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
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

echo_header() {
    echo ""
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║           ENHANCED VIBES STACK INSTALLER                     ║${NC}"
    echo -e "${MAGENTA}║                                                              ║${NC}"
    echo -e "${MAGENTA}║  Autocoder + Planning + Aleph + Enhanced UI + Quality Gates  ║${NC}"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER_MODE=true
            shift
            ;;
        --domain)
            DOMAIN="$2"
            shift
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --server        Full server deployment mode"
            echo "  --domain <name> Set custom domain for server mode"
            echo "  --help          Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo_header

if [ "$SERVER_MODE" = true ]; then
    echo -e "${CYAN}Mode: Production Server Setup${NC}"
    if [ -n "$DOMAIN" ]; then
        echo -e "${CYAN}Domain: $DOMAIN${NC}"
    fi
else
    echo -e "${CYAN}Mode: Local Development Setup${NC}"
fi

echo ""

# =============================================================================
# SERVER MODE: SYSTEM SETUP
# =============================================================================

if [ "$SERVER_MODE" = true ]; then
    # Check if running as root for server setup
    if [[ $EUID -ne 0 ]]; then
       echo_error "Server setup must be run as root (use sudo)"
       exit 1
    fi

    echo_step "Server mode: Setting up system..."

    # Check OS
    if ! command -v apt &> /dev/null; then
        echo_error "Server setup requires apt (Ubuntu/Debian)"
        exit 1
    fi

    # Update system
    echo_step "Updating system packages..."
    apt update && apt upgrade -y > /dev/null

    # Install system dependencies
    echo_step "Installing system dependencies..."
    apt install -y \
        curl \
        wget \
        git \
        htop \
        tmux \
        vim \
        unzip \
        jq \
        ca-certificates \
        gnupg \
        lsb-release \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        > /dev/null

    # Install Docker
    echo_step "Installing Docker..."
    if ! command -v docker &> /dev/null; then
        # Add Docker's official GPG key
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg

        # Add the repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null

        apt update > /dev/null
        apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null

        # Enable and start Docker
        systemctl enable docker
        systemctl start docker

        echo_success "Docker installed"
    else
        echo_success "Docker already installed"
    fi

    # Install Node.js
    echo_step "Installing Node.js..."
    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null
        apt install -y nodejs > /dev/null
    fi

    # Create vibes user
    echo_step "Creating vibes user..."
    if ! id "${VIBES_USER}" &>/dev/null; then
        useradd -m -s /bin/bash "${VIBES_USER}"
        usermod -aG docker "${VIBES_USER}"
        echo_success "User ${VIBES_USER} created"
    else
        echo_success "User ${VIBES_USER} already exists"
        usermod -aG docker "${VIBES_USER}"
    fi

    # Setup directories
    echo_step "Setting up directories..."
    mkdir -p "${PROJECTS_DIR}"
    mkdir -p "${VIBES_HOME}/.claude/logs"
    mkdir -p "${VIBES_HOME}/.claude/skills/learned"
    chown -R "${VIBES_USER}:${VIBES_USER}" "${VIBES_HOME}"

    # Configure firewall
    echo_step "Configuring firewall..."
    if command -v ufw &> /dev/null; then
        ufw --force enable
        ufw allow ssh
        ufw allow http
        ufw allow https
        echo_success "Firewall configured"
    fi

    # Switch to vibes user for the rest of the setup
    echo_step "Switching to vibes user for application setup..."
    AUTOCODER_DIR="${VIBES_HOME}/autocoder"
    PLANNING_DIR="${VIBES_HOME}/.claude/skills/planning-with-files"
fi

# =============================================================================
# COMMON SETUP: PREREQUISITES
# =============================================================================

echo_step "Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo_success "Python found: $PYTHON_VERSION"
else
    echo_error "Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo_success "pip found"
else
    echo_error "pip3 not found"
    exit 1
fi

# Check git
if command -v git &> /dev/null; then
    echo_success "git found"
else
    echo_error "git not found"
    exit 1
fi

# Install Claude CLI
echo_step "Installing Claude Code CLI..."
if ! command -v claude &> /dev/null; then
    if ! command -v npm &> /dev/null; then
        echo_error "npm not found. Install Node.js first."
        exit 1
    fi
    npm install -g @anthropic-ai/claude-code > /dev/null 2>&1 || echo_warning "Claude CLI install failed - install manually"
fi

if command -v claude &> /dev/null; then
    echo_success "Claude CLI found"
else
    echo_warning "Claude CLI not found - install with: npm install -g @anthropic-ai/claude-code"
fi

# =============================================================================
# PYTHON DEPENDENCIES
# =============================================================================

echo_step "Installing Python dependencies..."

PIP_INSTALL_CMD="pip3 install --user --break-system-packages --quiet"

# Core dependencies
$PIP_INSTALL_CMD sqlalchemy

# Aleph RLM
echo_step "Installing Aleph RLM..."
$PIP_INSTALL_CMD "aleph-rlm[mcp]" || {
    echo_warning "Could not install aleph-rlm from PyPI, trying GitHub..."
    $PIP_INSTALL_CMD "git+https://github.com/Hmbown/aleph.git#egg=aleph-rlm[mcp]" || {
        echo_warning "Could not install Aleph. Some features will be disabled."
    }
}

# MCP SDK
$PIP_INSTALL_CMD mcp || echo_warning "MCP SDK not installed"

# Enhanced cognitive processing dependencies
$PIP_INSTALL_CMD psutil docker || echo_warning "Optional dependencies not installed"

echo_success "Python dependencies installed"

# =============================================================================
# REPOSITORY SETUP
# =============================================================================

echo_step "Setting up repositories..."

# Function to run as vibes user if in server mode
run_as_user() {
    if [ "$SERVER_MODE" = true ]; then
        su - "${VIBES_USER}" -c "$1"
    else
        eval "$1"
    fi
}

# Autocoder
if [ -d "$AUTOCODER_DIR" ]; then
    echo_success "Autocoder already exists at $AUTOCODER_DIR"
else
    echo_step "Cloning autocoder..."
    run_as_user "git clone https://github.com/leonvanzyl/autocoder.git \"$AUTOCODER_DIR\""
    echo_success "Autocoder cloned"
fi

# Planning-with-Files skill
SKILLS_DIR="$(dirname "$PLANNING_DIR")"
run_as_user "mkdir -p \"$SKILLS_DIR\""

if [ -d "$PLANNING_DIR" ]; then
    echo_success "Planning-with-files already exists"
else
    echo_step "Installing planning-with-files skill..."
    run_as_user "git clone https://github.com/OthmanAdi/planning-with-files.git /tmp/planning-with-files-install"
    run_as_user "cp -r /tmp/planning-with-files-install/skills/planning-with-files \"$PLANNING_DIR\""
    run_as_user "rm -rf /tmp/planning-with-files-install"
    echo_success "Planning-with-files installed as Claude skill"
fi

# =============================================================================
# VIBES INTEGRATION FILES
# =============================================================================

echo_step "Installing Vibes integration files..."

# Copy integration files to autocoder
run_as_user "mkdir -p \"$AUTOCODER_DIR/mcp_server\""
run_as_user "cp \"$SCRIPT_DIR/mcp_server/\"* \"$AUTOCODER_DIR/mcp_server/\""

# Copy documentation
run_as_user "cp \"$SCRIPT_DIR/CLAUDE.md\" \"$AUTOCODER_DIR/\""

# Copy utility scripts
run_as_user "mkdir -p \"$AUTOCODER_DIR/scripts\""
if [ -f "$SCRIPT_DIR/scripts/init-session.sh" ]; then
    run_as_user "cp \"$SCRIPT_DIR/scripts/init-session.sh\" \"$AUTOCODER_DIR/scripts/\""
fi

echo_success "Integration files copied"

# =============================================================================
# CLAUDE DESKTOP CONFIGURATION
# =============================================================================

echo_step "Configuring Claude Desktop..."

CLAUDE_CONFIG_DIR="$HOME/.claude"
if [ "$SERVER_MODE" = true ]; then
    CLAUDE_CONFIG_DIR="${VIBES_HOME}/.claude"
fi

run_as_user "mkdir -p \"$CLAUDE_CONFIG_DIR\""

# Create MCP servers configuration
CLAUDE_MCP_CONFIG="$CLAUDE_CONFIG_DIR/mcp_servers.json"

run_as_user "cat > \"$CLAUDE_MCP_CONFIG\" << 'EOF'
{
  \"mcpServers\": {
    \"atom-of-thoughts\": {
      \"command\": \"npx\",
      \"args\": [
        \"-y\",
        \"@kbsooo/mcp-atom-of-thoughts\"
      ],
      \"description\": \"Enhanced reasoning through atomic thought decomposition\",
      \"env\": {}
    },
    \"sequential-thinking\": {
      \"command\": \"npx\",
      \"args\": [
        \"-y\",
        \"@modelcontextprotocol/server-sequentialthinking\"
      ],
      \"description\": \"Sequential reasoning chains for complex problem solving\",
      \"env\": {}
    },
    \"vibecoding-orchestrator\": {
      \"command\": \"python3\",
      \"args\": [
        \"$AUTOCODER_DIR/mcp_server/vibecoding_server.py\"
      ],
      \"description\": \"Vibes autonomous coding orchestration layer\",
      \"env\": {
        \"PYTHONPATH\": \"$AUTOCODER_DIR/mcp_server\"
      }
    },
    \"context7\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"@upstash/context7-mcp@latest\"]
    }
  },
  \"thinking\": {
    \"enabled\": true,
    \"preTaskAnalysis\": true,
    \"complexityThreshold\": 3,
    \"useAtomicThoughts\": true,
    \"useSequentialReasoning\": true
  }
}
EOF"

# Also create the Desktop app config format
CLAUDE_DESKTOP_DIR="$(dirname "$CLAUDE_CONFIG_DIR")/.config/claude-desktop"
if [ "$SERVER_MODE" = true ]; then
    CLAUDE_DESKTOP_DIR="${VIBES_HOME}/.config/claude-desktop"
fi

run_as_user "mkdir -p \"$CLAUDE_DESKTOP_DIR\""
run_as_user "cat > \"$CLAUDE_DESKTOP_DIR/claude_desktop_config.json\" << 'EOF'
{
  \"mcpServers\": {
    \"vibecoding\": {
      \"command\": \"python3\",
      \"args\": [\"$AUTOCODER_DIR/mcp_server/vibecoding_server.py\"]
    },
    \"context7\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"@upstash/context7-mcp@latest\"]
    }
  }
}
EOF"

echo_success "Claude configurations created"

# =============================================================================
# SERVER MODE: ENVIRONMENT SETUP
# =============================================================================

if [ "$SERVER_MODE" = true ]; then
    echo_step "Setting up server environment..."

    # Environment file
    if [[ ! -f "${SCRIPT_DIR}/deploy/.env" ]]; then
        cp "${SCRIPT_DIR}/deploy/env.example" "${SCRIPT_DIR}/deploy/.env" 2>/dev/null || true

        if [[ -f "${SCRIPT_DIR}/deploy/.env" ]]; then
            # Generate random secret key
            SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "your-secret-key-here")
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "${SCRIPT_DIR}/deploy/.env"

            # Set projects directory
            sed -i "s|PROJECTS_DIR=.*|PROJECTS_DIR=${PROJECTS_DIR}|" "${SCRIPT_DIR}/deploy/.env"

            # Set domain if provided
            if [ -n "$DOMAIN" ]; then
                sed -i "s/DOMAIN=.*/DOMAIN=${DOMAIN}/" "${SCRIPT_DIR}/deploy/.env"
            fi

            chown "${VIBES_USER}:${VIBES_USER}" "${SCRIPT_DIR}/deploy/.env"
            chmod 600 "${SCRIPT_DIR}/deploy/.env"

            echo_success "Environment configured"
        fi
    fi

    # tmux configuration
    cat > "${VIBES_HOME}/.tmux.conf" << 'EOF'
# Enhanced Vibes tmux configuration
set -g mouse on
set -g history-limit 50000
set -g base-index 1
setw -g pane-base-index 1

# Status bar
set -g status-bg black
set -g status-fg white
set -g status-left '[#S] '
set -g status-right '%H:%M %d-%b'

# Easy split
bind | split-window -h
bind - split-window -v

# Reload config
bind r source-file ~/.tmux.conf \; display "Config reloaded!"
EOF
    chown "${VIBES_USER}:${VIBES_USER}" "${VIBES_HOME}/.tmux.conf"

    echo_success "Server environment configured"
fi

# =============================================================================
# VERIFICATION
# =============================================================================

echo_step "Verifying installation..."

# Test Python imports
python3 -c "import sqlalchemy; print('✓ SQLAlchemy:', sqlalchemy.__version__)" 2>/dev/null || echo_warning "SQLAlchemy test failed"
python3 -c "import aleph; print('✓ Aleph:', aleph.__version__)" 2>/dev/null || echo_warning "Aleph test skipped"

# Check skills
if [ -f "$PLANNING_DIR/SKILL.md" ]; then
    echo_success "Planning-with-files skill verified"
else
    echo_warning "Planning-with-files SKILL.md not found"
fi

# Check MCP files
if [ -f "$AUTOCODER_DIR/mcp_server/vibecoding_server.py" ]; then
    echo_success "Vibes MCP server verified"
else
    echo_warning "Vibes MCP server not found"
fi

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ENHANCED VIBES STACK INSTALLATION COMPLETE         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$SERVER_MODE" = true ]; then
    echo -e "${CYAN}Server Installation Complete!${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Edit environment configuration:"
    echo "   sudo -u ${VIBES_USER} nano ${SCRIPT_DIR}/deploy/.env"
    echo ""
    echo "2. Start the enhanced stack:"
    echo "   cd ${SCRIPT_DIR}/deploy"
    echo "   docker compose up -d"
    echo ""
    echo "3. Start a development session:"
    echo "   su - ${VIBES_USER}"
    echo "   cd ~/autocoder"
    echo "   ./start.sh"
    echo ""
    echo "Services will be available at:"
    if [ -n "$DOMAIN" ]; then
        echo "  - Main UI:   https://$DOMAIN"
        echo "  - Dashboard: https://dash.$DOMAIN"
    else
        echo "  - Configure domain in .env file first"
    fi
    echo ""
else
    echo -e "${CYAN}Local Development Installation Complete!${NC}"
    echo ""
    echo "Stack components installed:"
    echo "  - Autocoder:        $AUTOCODER_DIR"
    echo "  - Planning skill:   $PLANNING_DIR"
    echo "  - MCP servers:      $CLAUDE_CONFIG_DIR/mcp_servers.json"
    echo "  - Claude Desktop:   ~/.config/claude-desktop/claude_desktop_config.json"
    echo ""
    echo "To start developing:"
    echo ""
    echo "  cd $AUTOCODER_DIR"
    echo "  ./start.sh"
    echo ""
    echo "Or with the Web UI:"
    echo ""
    echo "  ./start_ui.sh"
    echo ""
fi

echo "Enhanced features now available:"
echo "  🤖 Real-time agent monitoring"
echo "  ⚡ One-click development actions"
echo "  🧠 Natural language configuration"
echo "  🔬 Cognitive processing enhancement"
echo "  ✅ Production quality gates"
echo "  🖥️ System health monitoring"
echo ""
echo "See CLAUDE.md for detailed usage instructions."
echo ""