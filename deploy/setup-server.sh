#!/bin/bash
# Vibes Stack - Server Setup Script
# ==================================
# Provisions a fresh Ubuntu/Debian server with the full vibes stack.
#
# Tested on:
#   - Ubuntu 22.04 / 24.04
#   - Debian 12
#   - Hetzner Cloud / Dedicated
#   - DigitalOcean
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/yourusername/vibes/main/deploy/setup-server.sh | bash
#   # Or:
#   ./setup-server.sh
#
# After running:
#   1. Edit /home/vibes/vibes/deploy/.env
#   2. Run: cd /home/vibes/vibes/deploy && docker compose up -d

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[VIBES]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ===========================================
# Configuration
# ===========================================
VIBES_USER="vibes"
VIBES_HOME="/home/${VIBES_USER}"
VIBES_REPO="https://github.com/StreetsDigital/vibes.git"
PROJECTS_DIR="${VIBES_HOME}/projects"

# ===========================================
# Pre-flight checks
# ===========================================
log "Starting Vibes Stack setup..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

# Check OS
if ! command -v apt &> /dev/null; then
    error "This script requires apt (Ubuntu/Debian)"
fi

# ===========================================
# System Updates
# ===========================================
log "Updating system packages..."
apt update && apt upgrade -y

# ===========================================
# Install Dependencies
# ===========================================
log "Installing dependencies..."
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
    build-essential

# ===========================================
# Install Docker
# ===========================================
log "Installing Docker..."
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

    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    log "Docker installed successfully"
else
    log "Docker already installed"
fi

# ===========================================
# Create Vibes User
# ===========================================
log "Creating vibes user..."
if ! id "${VIBES_USER}" &>/dev/null; then
    useradd -m -s /bin/bash "${VIBES_USER}"
    usermod -aG docker "${VIBES_USER}"
    log "User ${VIBES_USER} created"
else
    log "User ${VIBES_USER} already exists"
    usermod -aG docker "${VIBES_USER}"
fi

# ===========================================
# Setup Directory Structure
# ===========================================
log "Setting up directories..."
mkdir -p "${PROJECTS_DIR}"
mkdir -p "${VIBES_HOME}/.claude/logs"
mkdir -p "${VIBES_HOME}/.claude/skills/learned"
chown -R "${VIBES_USER}:${VIBES_USER}" "${VIBES_HOME}"

# ===========================================
# Clone Vibes Repository
# ===========================================
log "Cloning vibes repository..."
if [[ ! -d "${VIBES_HOME}/vibes" ]]; then
    su - "${VIBES_USER}" -c "git clone ${VIBES_REPO} ${VIBES_HOME}/vibes"
else
    log "Vibes repo already exists, pulling latest..."
    su - "${VIBES_USER}" -c "cd ${VIBES_HOME}/vibes && git pull"
fi

# ===========================================
# Setup Environment
# ===========================================
log "Setting up environment..."
if [[ ! -f "${VIBES_HOME}/vibes/deploy/.env" ]]; then
    cp "${VIBES_HOME}/vibes/deploy/env.example" "${VIBES_HOME}/vibes/deploy/.env"

    # Generate random secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "${VIBES_HOME}/vibes/deploy/.env"

    # Set projects directory
    sed -i "s|PROJECTS_DIR=.*|PROJECTS_DIR=${PROJECTS_DIR}|" "${VIBES_HOME}/vibes/deploy/.env"

    chown "${VIBES_USER}:${VIBES_USER}" "${VIBES_HOME}/vibes/deploy/.env"
    chmod 600 "${VIBES_HOME}/vibes/deploy/.env"

    warn "Created .env file - EDIT IT with your domain and API keys!"
fi

# ===========================================
# Install Claude Code CLI
# ===========================================
log "Installing Claude Code CLI..."
if ! command -v claude &> /dev/null; then
    # Install Node.js if needed
    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y nodejs
    fi

    npm install -g @anthropic-ai/claude-code
    log "Claude Code CLI installed"
else
    log "Claude Code CLI already installed"
fi

# ===========================================
# Setup tmux Configuration
# ===========================================
log "Setting up tmux..."
cat > "${VIBES_HOME}/.tmux.conf" << 'EOF'
# Vibes tmux configuration
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

# ===========================================
# Setup Vibes Session Script
# ===========================================
log "Creating vibes session script..."
cat > "${VIBES_HOME}/start-vibes.sh" << 'EOF'
#!/bin/bash
# Start a vibes tmux session with standard windows

SESSION="vibes"

# Check if session exists
tmux has-session -t $SESSION 2>/dev/null

if [ $? != 0 ]; then
    # Create new session
    tmux new-session -d -s $SESSION -n claude

    # Window 1: Claude Code
    tmux send-keys -t $SESSION:claude "cd ~/projects && claude" Enter

    # Window 2: Shell
    tmux new-window -t $SESSION -n shell
    tmux send-keys -t $SESSION:shell "cd ~/projects" Enter

    # Window 3: Logs
    tmux new-window -t $SESSION -n logs
    tmux send-keys -t $SESSION:logs "cd ~/vibes/deploy && docker compose logs -f" Enter

    # Window 4: Monitor
    tmux new-window -t $SESSION -n monitor
    tmux send-keys -t $SESSION:monitor "htop" Enter

    # Select first window
    tmux select-window -t $SESSION:claude
fi

# Attach to session
tmux attach-session -t $SESSION
EOF
chmod +x "${VIBES_HOME}/start-vibes.sh"
chown "${VIBES_USER}:${VIBES_USER}" "${VIBES_HOME}/start-vibes.sh"

# ===========================================
# Setup Firewall
# ===========================================
log "Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow ssh
    ufw allow http
    ufw allow https
    log "Firewall configured (SSH, HTTP, HTTPS allowed)"
fi

# ===========================================
# Install Tailscale (Optional)
# ===========================================
log "Installing Tailscale..."
if ! command -v tailscale &> /dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
    log "Tailscale installed - run 'sudo tailscale up' to connect"
else
    log "Tailscale already installed"
fi

# ===========================================
# Final Instructions
# ===========================================
echo ""
echo "=========================================="
echo -e "${GREEN}Vibes Stack Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit the environment file:"
echo "   sudo -u vibes nano ${VIBES_HOME}/vibes/deploy/.env"
echo ""
echo "2. Set your domain, API keys, and passwords"
echo ""
echo "3. Start the stack:"
echo "   cd ${VIBES_HOME}/vibes/deploy"
echo "   docker compose up -d"
echo ""
echo "4. (Optional) Connect Tailscale:"
echo "   sudo tailscale up"
echo ""
echo "5. Start a vibes session:"
echo "   su - vibes"
echo "   ./start-vibes.sh"
echo ""
echo "Services will be available at:"
echo "  - Kanban:    https://\${DOMAIN}"
echo "  - Dashboard: https://dash.\${DOMAIN}"
echo ""
echo "=========================================="
