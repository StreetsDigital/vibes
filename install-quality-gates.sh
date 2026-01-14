#!/usr/bin/env bash
#
# Vibecoding Stack - Quality Gates Extension Installer
# =====================================================
#
# Adds production-ready quality gates to your vibecoding stack:
# - Pre-commit hooks (secrets, format, lint, types)
# - GitHub Actions CI/CD workflow
# - Claude Code hooks for auto-formatting
# - Quality gate MCP tools
# - Verification agent
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOCODER_DIR="${AUTOCODER_DIR:-$HOME/autocoder}"
PROJECT_DIR="${1:-$(pwd)}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_step() {
    echo -e "${BLUE}==>${NC} $1"
}

echo_success() {
    echo -e "${GREEN}✔${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo_error() {
    echo -e "${RED}✖${NC} $1"
}

# =============================================================================
# HEADER
# =============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       VIBECODING STACK - QUALITY GATES EXTENSION           ║"
echo "║                                                            ║"
echo "║  Adding production-ready quality gates to your stack       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Target project: $PROJECT_DIR"
echo "  Autocoder dir:  $AUTOCODER_DIR"
echo ""

# =============================================================================
# CHECKS
# =============================================================================

echo_step "Checking prerequisites..."

# Check if autocoder exists
if [ ! -d "$AUTOCODER_DIR" ]; then
    echo_warning "Autocoder not found at $AUTOCODER_DIR"
    echo "  Run the main setup.sh first, or set AUTOCODER_DIR"
fi

# Check if project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

echo_success "Prerequisites OK"

# =============================================================================
# INSTALL QUALITY GATES MODULE
# =============================================================================

echo_step "Installing quality gates module..."

# Copy quality_gates.py to mcp_server
mkdir -p "$AUTOCODER_DIR/mcp_server"
cp "$SCRIPT_DIR/quality_gates.py" "$AUTOCODER_DIR/mcp_server/"
echo_success "Copied quality_gates.py"

# Copy updated MCP server
cp "$SCRIPT_DIR/mcp_server/feature_mcp_quality.py" "$AUTOCODER_DIR/mcp_server/"
echo_success "Copied feature_mcp_quality.py"

# Copy CLAUDE.md with quality gates
cp "$SCRIPT_DIR/CLAUDE_QUALITY.md" "$AUTOCODER_DIR/CLAUDE.md"
echo_success "Updated CLAUDE.md with quality gates"

# =============================================================================
# INSTALL GIT HOOKS
# =============================================================================

echo_step "Installing git hooks..."

cd "$PROJECT_DIR"

# Check if git repo
if [ -d ".git" ]; then
    mkdir -p .git/hooks
    
    # Copy pre-commit hook
    cp "$SCRIPT_DIR/hooks/pre-commit" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo_success "Installed pre-commit hook"
else
    echo_warning "Not a git repository, skipping hooks"
fi

# =============================================================================
# INSTALL GITHUB ACTIONS
# =============================================================================

echo_step "Installing GitHub Actions workflow..."

mkdir -p "$PROJECT_DIR/.github/workflows"
cp "$SCRIPT_DIR/.github/workflows/quality-gates.yml" "$PROJECT_DIR/.github/workflows/"
echo_success "Installed quality-gates.yml workflow"

# =============================================================================
# INSTALL CLAUDE CODE CONFIG
# =============================================================================

echo_step "Installing Claude Code configuration..."

mkdir -p "$PROJECT_DIR/.claude"

# Copy settings.json
cp "$SCRIPT_DIR/.claude/settings.json" "$PROJECT_DIR/.claude/"
echo_success "Installed Claude Code settings.json"

# Copy slash commands
mkdir -p "$PROJECT_DIR/.claude/commands"
cp "$SCRIPT_DIR/.claude/commands/"*.md "$PROJECT_DIR/.claude/commands/" 2>/dev/null || true
echo_success "Installed slash commands"

# =============================================================================
# INSTALL QUALITY CONFIG
# =============================================================================

echo_step "Installing quality gate configuration..."

cp "$SCRIPT_DIR/quality-gate.config.json" "$PROJECT_DIR/"
echo_success "Installed quality-gate.config.json"

# =============================================================================
# DETECT AND CONFIGURE PROJECT TYPE
# =============================================================================

echo_step "Detecting project type..."

cd "$PROJECT_DIR"

if [ -f "package.json" ]; then
    echo_success "Detected Node.js project"
    
    # Check for required scripts
    echo_step "Checking package.json scripts..."
    
    # Suggest missing scripts
    if ! grep -q '"lint"' package.json; then
        echo_warning "Missing 'lint' script. Add: \"lint\": \"eslint .\""
    fi
    
    if ! grep -q '"format"' package.json && ! grep -q '"prettier"' package.json; then
        echo_warning "Missing format script. Add: \"format\": \"prettier --write .\""
    fi
    
    if [ -f "tsconfig.json" ] && ! grep -q '"typecheck"' package.json; then
        echo_warning "Missing 'typecheck' script. Add: \"typecheck\": \"tsc --noEmit\""
    fi
    
    # Install dev dependencies if needed
    echo_step "Checking dev dependencies..."
    
    if ! grep -q '"prettier"' package.json; then
        echo_warning "Consider installing prettier: npm i -D prettier"
    fi
    
    if ! grep -q '"eslint"' package.json; then
        echo_warning "Consider installing eslint: npm i -D eslint"
    fi

elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    echo_success "Detected Python project"
    
    echo_step "Checking Python tools..."
    
    if ! command -v ruff &> /dev/null && ! command -v pylint &> /dev/null; then
        echo_warning "Consider installing ruff: pip install ruff"
    fi
    
    if ! command -v black &> /dev/null; then
        echo_warning "Consider installing black: pip install black"
    fi
    
    if ! command -v mypy &> /dev/null; then
        echo_warning "Consider installing mypy: pip install mypy"
    fi
    
    if ! command -v pytest &> /dev/null; then
        echo_warning "Consider installing pytest: pip install pytest pytest-cov"
    fi

elif [ -f "go.mod" ]; then
    echo_success "Detected Go project"
    
    echo_step "Checking Go tools..."
    
    if ! command -v golangci-lint &> /dev/null; then
        echo_warning "Consider installing golangci-lint:"
        echo "  go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"
    fi

else
    echo_warning "Unknown project type. Quality checks will use defaults."
fi

# =============================================================================
# CREATE .gitignore ADDITIONS
# =============================================================================

echo_step "Updating .gitignore..."

GITIGNORE_ADDITIONS="
# Quality gates
.claude/logs/
quality-gate-results.json
coverage/
.nyc_output/
htmlcov/
.coverage
*.lcov
"

if [ -f ".gitignore" ]; then
    # Check if already added
    if ! grep -q "Quality gates" .gitignore; then
        echo "$GITIGNORE_ADDITIONS" >> .gitignore
        echo_success "Updated .gitignore"
    else
        echo_success ".gitignore already configured"
    fi
else
    echo "$GITIGNORE_ADDITIONS" > .gitignore
    echo_success "Created .gitignore"
fi

# =============================================================================
# SETUP GITHUB SECRETS REMINDER
# =============================================================================

echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  ${GREEN}Quality Gates Extension Installed!${NC}"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  ${BLUE}What's installed:${NC}"
echo "    ✔ Quality gates module (tests, lint, types, security)"
echo "    ✔ Pre-commit hook (blocks secrets, checks format)"
echo "    ✔ GitHub Actions workflow (CI quality gates)"
echo "    ✔ Claude Code hooks (auto-format on edit)"
echo "    ✔ Slash commands (/verify, /commit)"
echo ""
echo "  ${BLUE}To enable Claude AI code review in CI:${NC}"
echo "    1. Go to GitHub repo → Settings → Secrets"
echo "    2. Add secret: ANTHROPIC_API_KEY"
echo ""
echo "  ${BLUE}Usage:${NC}"
echo ""
echo "    # Run quick quality check"
echo "    quality_check(quick=True)"
echo ""
echo "    # Run full quality check"
echo "    quality_check()"
echo ""
echo "    # Verify feature before marking complete"
echo "    feature_verify(feature_id)"
echo ""
echo "    # Mark complete (auto-runs quality checks)"
echo "    feature_mark_passing(feature_id)"
echo ""
echo "  ${BLUE}Slash commands:${NC}"
echo "    /verify  - Run quality verification"
echo "    /commit  - Commit with quality checks"
echo ""
echo "  ${BLUE}Git hooks:${NC}"
echo "    Pre-commit: secrets, format, lint, types"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
