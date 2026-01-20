#!/usr/bin/env bash
#
# Lightsail + Mobile (Termius) Setup
# ==================================
# One-command setup for vibecoding from your phone
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/StreetsDigital/vibes/master/lightsail/setup.sh | bash
#   OR
#   ./lightsail/setup.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo_step() { echo -e "${BLUE}==>${NC} $1"; }
echo_success() { echo -e "${GREEN}✓${NC} $1"; }
echo_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
echo_error() { echo -e "${RED}✗${NC} $1"; }

# Detect package manager
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    INSTALL_CMD="sudo apt-get install -y"
    UPDATE_CMD="sudo apt-get update"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    INSTALL_CMD="sudo yum install -y"
    UPDATE_CMD="sudo yum update -y"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="sudo dnf install -y"
    UPDATE_CMD="sudo dnf update -y"
else
    echo_error "Unsupported package manager"
    exit 1
fi

echo ""
echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║           LIGHTSAIL + MOBILE SETUP                           ║${NC}"
echo -e "${MAGENTA}║                                                              ║${NC}"
echo -e "${MAGENTA}║  Vibecoding from your phone with Termius                     ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# SYSTEM PACKAGES
# =============================================================================

echo_step "Updating system packages..."
$UPDATE_CMD > /dev/null 2>&1

echo_step "Installing dependencies..."
$INSTALL_CMD \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    jq \
    tmux \
    htop \
    tree \
    unzip \
    build-essential \
    > /dev/null 2>&1 || true

echo_success "System packages installed"

# =============================================================================
# PYTHON DEPENDENCIES
# =============================================================================

echo_step "Installing Python dependencies..."
pip3 install --user --quiet --break-system-packages \
    sqlalchemy \
    mcp \
    "aleph-rlm[mcp]" 2>/dev/null || \
    pip3 install --user --quiet --break-system-packages \
        sqlalchemy \
        mcp \
        "git+https://github.com/Hmbown/aleph.git#egg=aleph-rlm[mcp]" 2>/dev/null || true

echo_success "Python dependencies installed"

# =============================================================================
# CLAUDE CODE CLI
# =============================================================================

echo_step "Installing Claude Code CLI..."
if ! command -v claude &> /dev/null; then
    # Install via npm (if Node exists) or direct download
    if command -v npm &> /dev/null; then
        npm install -g @anthropic-ai/claude-code 2>/dev/null || true
    else
        # Install Node.js first (LTS)
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null 2>&1
        $INSTALL_CMD nodejs > /dev/null 2>&1
        npm install -g @anthropic-ai/claude-code 2>/dev/null || true
    fi
fi

if command -v claude &> /dev/null; then
    echo_success "Claude Code CLI installed"
else
    echo_warning "Claude Code CLI not installed - install manually with: npm i -g @anthropic-ai/claude-code"
fi

# =============================================================================
# VIBECODING STACK
# =============================================================================

echo_step "Setting up Vibecoding Stack..."

VIBE_HOME="$HOME/vibecoding"
mkdir -p "$VIBE_HOME"

# Clone autocoder
if [ ! -d "$VIBE_HOME/autocoder" ]; then
    git clone -q https://github.com/leonvanzyl/autocoder.git "$VIBE_HOME/autocoder"
fi

# Clone planning-with-files
mkdir -p "$HOME/.claude/skills"
if [ ! -d "$HOME/.claude/skills/planning-with-files" ]; then
    git clone -q https://github.com/OthmanAdi/planning-with-files.git /tmp/planning-with-files
    cp -r /tmp/planning-with-files/planning-with-files "$HOME/.claude/skills/"
    rm -rf /tmp/planning-with-files
fi

echo_success "Vibecoding Stack installed to $VIBE_HOME"

# =============================================================================
# TMUX CONFIG (Critical for mobile!)
# =============================================================================

echo_step "Configuring tmux for mobile..."

cat > "$HOME/.tmux.conf" << 'EOF'
# Vibecoding Mobile tmux Config
# =============================
# Optimized for Termius on phone

# Use Ctrl+a as prefix (easier on phone)
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# Easy window navigation
bind -n M-Left select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up select-pane -U
bind -n M-Down select-pane -D

# Window shortcuts
bind -n M-1 select-window -t 1
bind -n M-2 select-window -t 2
bind -n M-3 select-window -t 3
bind -n M-4 select-window -t 4

# Split panes with | and -
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"

# Reload config
bind r source-file ~/.tmux.conf \; display "Config reloaded!"

# Mouse support (helpful on mobile)
set -g mouse on

# Larger history
set -g history-limit 50000

# Start windows at 1 (easier to reach on phone keyboard)
set -g base-index 1
setw -g pane-base-index 1

# Auto-rename windows
setw -g automatic-rename on
set -g renumber-windows on

# Status bar - clean and informative
set -g status-position bottom
set -g status-style 'bg=#1a1b26 fg=#a9b1d6'
set -g status-left '#[fg=#7aa2f7,bold] #S '
set -g status-right '#[fg=#9ece6a]%H:%M #[fg=#7aa2f7]%d-%b'
set -g status-left-length 30
set -g status-right-length 50

# Window status
setw -g window-status-current-style 'fg=#1a1b26 bg=#7aa2f7 bold'
setw -g window-status-current-format ' #I:#W '
setw -g window-status-style 'fg=#a9b1d6'
setw -g window-status-format ' #I:#W '

# Pane borders
set -g pane-border-style 'fg=#3b4261'
set -g pane-active-border-style 'fg=#7aa2f7'

# Activity alerts
setw -g monitor-activity on
set -g visual-activity off

# Quick session commands
bind S new-session
bind K kill-session

# Vim-style copy mode
setw -g mode-keys vi
bind -T copy-mode-vi v send -X begin-selection
bind -T copy-mode-vi y send -X copy-selection-and-cancel

# Quick pane zoom (double tap prefix)
bind C-a resize-pane -Z
EOF

echo_success "tmux configured"

# =============================================================================
# MOBILE HELPER SCRIPTS
# =============================================================================

echo_step "Creating mobile helper scripts..."

mkdir -p "$HOME/bin"

# Quick start script
cat > "$HOME/bin/vibe" << 'EOF'
#!/usr/bin/env bash
# Quick vibecoding session starter
# Usage: vibe [project-name]

PROJECT="${1:-default}"
SESSION="vibe-$PROJECT"

# Check if session exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Attaching to existing session: $SESSION"
    tmux attach -t "$SESSION"
else
    echo "Creating new session: $SESSION"

    # Create session with project window
    tmux new-session -d -s "$SESSION" -n "claude" -c "$HOME/projects/$PROJECT"

    # Create projects dir if needed
    mkdir -p "$HOME/projects/$PROJECT"

    # Add a shell window
    tmux new-window -t "$SESSION" -n "shell" -c "$HOME/projects/$PROJECT"

    # Add a monitoring window
    tmux new-window -t "$SESSION" -n "logs" -c "$HOME/projects/$PROJECT"

    # Add an exploration/scratchpad window
    tmux new-window -t "$SESSION" -n "scratch" -c "$HOME/projects/$PROJECT"

    # Go back to first window
    tmux select-window -t "$SESSION:1"

    # Attach
    tmux attach -t "$SESSION"
fi
EOF

chmod +x "$HOME/bin/vibe"

# List sessions
cat > "$HOME/bin/vibe-list" << 'EOF'
#!/usr/bin/env bash
# List all vibecoding sessions
echo "Active Sessions:"
echo "================"
tmux list-sessions 2>/dev/null || echo "No active sessions"
echo ""
echo "Quick commands:"
echo "  vibe <project>  - Start/attach to project"
echo "  vibe-kill <name> - Kill a session"
EOF

chmod +x "$HOME/bin/vibe-list"

# Kill session
cat > "$HOME/bin/vibe-kill" << 'EOF'
#!/usr/bin/env bash
# Kill a vibecoding session
if [ -z "$1" ]; then
    echo "Usage: vibe-kill <session-name>"
    echo ""
    tmux list-sessions 2>/dev/null
    exit 1
fi
tmux kill-session -t "$1" 2>/dev/null && echo "Killed: $1" || echo "Session not found: $1"
EOF

chmod +x "$HOME/bin/vibe-kill"

# Add bin to PATH
if ! grep -q 'HOME/bin' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
fi

echo_success "Helper scripts created"

# =============================================================================
# SSH HARDENING
# =============================================================================

echo_step "Checking SSH configuration..."

# Create .ssh if needed
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Check for existing keys
if [ ! -f "$HOME/.ssh/authorized_keys" ]; then
    touch "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
    echo_warning "No SSH keys found - add your Termius public key!"
fi

echo_success "SSH directory configured"

# =============================================================================
# PROJECTS DIRECTORY
# =============================================================================

mkdir -p "$HOME/projects"
echo_success "Projects directory created at ~/projects"

# =============================================================================
# WELCOME MESSAGE
# =============================================================================

cat > "$HOME/.vibe-welcome" << 'EOF'

╔══════════════════════════════════════════════════════════════╗
║           VIBECODING MOBILE ENVIRONMENT                      ║
╚══════════════════════════════════════════════════════════════╝

Quick Start:
  vibe <project>     Start/resume a coding session
  vibe-list          List active sessions
  vibe-kill <name>   Kill a session

Windows:
  1:claude   Main coding session
  2:shell    Git, npm, terminal commands
  3:logs     Watch builds, tests, output
  4:scratch  Exploration & experiments

tmux Shortcuts (prefix = Ctrl+a):
  Ctrl+a 1-4         Switch windows
  Ctrl+a d           Detach (session keeps running!)
  Ctrl+a |           Split horizontal
  Ctrl+a -           Split vertical
  Ctrl+a Ctrl+a      Toggle zoom

Inside a session:
  claude             Start Claude Code
  cd ~/projects      Your projects

Happy vibecoding! 📱

EOF

# Add welcome to bashrc
if ! grep -q 'vibe-welcome' "$HOME/.bashrc" 2>/dev/null; then
    echo 'cat "$HOME/.vibe-welcome" 2>/dev/null' >> "$HOME/.bashrc"
fi

# =============================================================================
# DONE!
# =============================================================================

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           SETUP COMPLETE!                                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Add your Termius SSH key:"
echo "     ${CYAN}echo 'your-public-key' >> ~/.ssh/authorized_keys${NC}"
echo ""
echo "  2. Configure Termius:"
echo "     - Host: $(curl -s ifconfig.me 2>/dev/null || echo '<your-lightsail-ip>')"
echo "     - Port: 22"
echo "     - Username: $(whoami)"
echo ""
echo "  3. Start coding:"
echo "     ${CYAN}vibe my-project${NC}"
echo "     ${CYAN}claude${NC}"
echo ""
echo "  4. When done, detach (Ctrl+a d) - session keeps running!"
echo ""
