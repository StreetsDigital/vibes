#!/usr/bin/env bash
#
# Test Vibecode Stack Flow
# =========================
# Verifies each component of the stack is working
#
# Usage: ./scripts/test-flow.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

test_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    PASS=$((PASS + 1))
}

test_fail() {
    echo -e "  ${RED}✗${NC} $1"
    FAIL=$((FAIL + 1))
}

test_skip() {
    echo -e "  ${YELLOW}○${NC} $1 (skipped)"
}

section() {
    echo ""
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

# =============================================================================
section "1. Directory Structure"
# =============================================================================

# Check vibes repo structure
if [ -f "./vibecode" ]; then
    test_pass "vibecode script exists"
else
    test_fail "vibecode script missing"
fi

if [ -d "./.claude" ]; then
    test_pass ".claude directory exists"
else
    test_fail ".claude directory missing"
fi

if [ -f "./.claude/settings.json" ]; then
    test_pass "settings.json exists"
else
    test_fail "settings.json missing"
fi

if [ -d "./.claude/skills" ]; then
    test_pass "skills directory exists"
else
    test_fail "skills directory missing"
fi

if [ -f "./.claude/skills/continuous-learning/SKILL.md" ]; then
    test_pass "continuous-learning skill exists"
else
    test_fail "continuous-learning skill missing"
fi

if [ -d "./.claude/commands" ]; then
    test_pass "commands directory exists"
else
    test_fail "commands directory missing"
fi

# =============================================================================
section "2. Slash Commands"
# =============================================================================

if [ -f "./.claude/commands/verify.md" ]; then
    test_pass "/verify command exists"
else
    test_fail "/verify command missing"
fi

if [ -f "./.claude/commands/commit.md" ]; then
    test_pass "/commit command exists"
else
    test_fail "/commit command missing"
fi

if [ -f "./.claude/commands/retrospective.md" ]; then
    test_pass "/retrospective command exists"
else
    test_fail "/retrospective command missing"
fi

# =============================================================================
section "3. Settings Configuration"
# =============================================================================

if grep -q "autoApproveWrites" ./.claude/settings.json 2>/dev/null; then
    if grep -q '"autoApproveWrites": true' ./.claude/settings.json 2>/dev/null; then
        test_pass "autoApproveWrites enabled"
    else
        test_fail "autoApproveWrites disabled"
    fi
else
    test_fail "autoApproveWrites not configured"
fi

if grep -q "Stop" ./.claude/settings.json 2>/dev/null; then
    test_pass "Stop hooks configured"
else
    test_fail "Stop hooks missing"
fi

if grep -q "retrospective" ./.claude/settings.json 2>/dev/null; then
    test_pass "Learning hook configured"
else
    test_fail "Learning hook missing"
fi

# =============================================================================
section "4. Global Skills Directory"
# =============================================================================

GLOBAL_SKILLS="$HOME/.claude/skills/learned"

if [ -d "$GLOBAL_SKILLS" ]; then
    test_pass "Global skills directory exists: $GLOBAL_SKILLS"
else
    mkdir -p "$GLOBAL_SKILLS"
    test_pass "Global skills directory created: $GLOBAL_SKILLS"
fi

# Test write access
TEST_FILE="$GLOBAL_SKILLS/.test-$$"
if touch "$TEST_FILE" 2>/dev/null; then
    rm -f "$TEST_FILE"
    test_pass "Global skills directory is writable"
else
    test_fail "Global skills directory not writable"
fi

# Count existing skills
SKILL_COUNT=$(find "$GLOBAL_SKILLS" -name "*.md" 2>/dev/null | wc -l)
echo -e "  ${BLUE}ℹ${NC} $SKILL_COUNT skills currently saved"

# =============================================================================
section "5. MCP Server"
# =============================================================================

if [ -d "./mcp_server" ]; then
    test_pass "mcp_server directory exists"
else
    test_fail "mcp_server directory missing"
fi

if [ -f "./mcp_server/vibecoding_server.py" ]; then
    test_pass "vibecoding_server.py exists"
else
    test_fail "vibecoding_server.py missing"
fi

if [ -f "./mcp_server/quality_gates.py" ]; then
    test_pass "quality_gates.py exists"
else
    test_fail "quality_gates.py missing"
fi

if [ -f "./mcp_server/aleph_bridge.py" ]; then
    test_pass "aleph_bridge.py exists"
else
    test_fail "aleph_bridge.py missing"
fi

# =============================================================================
section "6. Quality Gates"
# =============================================================================

if [ -f "./quality-gate.config.json" ]; then
    test_pass "quality-gate.config.json exists"
else
    test_fail "quality-gate.config.json missing"
fi

if [ -f "./hooks/pre-commit" ]; then
    test_pass "pre-commit hook exists"
    if [ -x "./hooks/pre-commit" ]; then
        test_pass "pre-commit hook is executable"
    else
        test_fail "pre-commit hook not executable"
    fi
else
    test_fail "pre-commit hook missing"
fi

# Check if pre-commit is installed in .git/hooks
if [ -f "./.git/hooks/pre-commit" ]; then
    test_pass "pre-commit installed in .git/hooks"
else
    test_skip "pre-commit not installed in .git/hooks (run: cp hooks/pre-commit .git/hooks/)"
fi

# =============================================================================
section "7. Docker/ClaudeBox (Optional)"
# =============================================================================

if command -v docker &>/dev/null; then
    test_pass "Docker is installed"

    if docker info &>/dev/null; then
        test_pass "Docker daemon is running"
    else
        test_fail "Docker daemon not running"
    fi
else
    test_skip "Docker not installed (needed for ClaudeBox isolation)"
fi

if command -v claudebox &>/dev/null; then
    test_pass "ClaudeBox is installed"
else
    test_skip "ClaudeBox not installed (run: vibecode init)"
fi

# =============================================================================
section "8. Claude Code CLI"
# =============================================================================

if command -v claude &>/dev/null; then
    test_pass "Claude Code CLI is installed"

    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo -e "  ${BLUE}ℹ${NC} Version: $CLAUDE_VERSION"
else
    test_fail "Claude Code CLI not installed"
    echo -e "  ${YELLOW}→${NC} Install: npm install -g @anthropic-ai/claude-code"
fi

# =============================================================================
section "9. Documentation"
# =============================================================================

for doc in README.md CLAUDE.md QUICK_START.md; do
    if [ -f "./$doc" ]; then
        test_pass "$doc exists"
    else
        test_fail "$doc missing"
    fi
done

# =============================================================================
section "Results"
# =============================================================================

echo ""
TOTAL=$((PASS + FAIL))
echo -e "${GREEN}Passed: $PASS${NC} / ${RED}Failed: $FAIL${NC} / Total: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "Your stack is ready. Start coding:"
    echo ""
    echo "  Server:     cd ~/autocoder && claude"
    echo "  ClaudeBox:  vibecode new my-project python && vibecode code my-project"
    echo ""
    exit 0
else
    echo -e "${YELLOW}Some tests failed. Review the output above.${NC}"
    exit 1
fi
