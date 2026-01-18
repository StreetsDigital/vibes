#!/usr/bin/env bash
#
# Test Learning/Skills Sharing Flow
# ==================================
# Verifies that skills can be saved and shared across projects
#
# Usage: ./scripts/test-learning.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}━━━ Testing Learning/Skills Flow ━━━${NC}"
echo ""

GLOBAL_SKILLS="$HOME/.claude/skills/learned"
TEST_SKILL="test-skill-$(date +%s)"

# =============================================================================
echo -e "${BLUE}1. Setup${NC}"
# =============================================================================

# Ensure directory exists
mkdir -p "$GLOBAL_SKILLS"
echo -e "  ${GREEN}✓${NC} Global skills directory: $GLOBAL_SKILLS"

# =============================================================================
echo -e "${BLUE}2. Create Test Skill${NC}"
# =============================================================================

cat > "$GLOBAL_SKILLS/$TEST_SKILL.md" << EOF
---
name: $TEST_SKILL
description: Test skill for verifying learning flow
author: test-script
version: 1.0.0
created: $(date -Iseconds)
---

# Test Skill

## Trigger
This is a test skill created by test-learning.sh

## Solution
If you can read this, the learning flow is working.

## Verification
Check that this file exists in the global skills directory.
EOF

if [ -f "$GLOBAL_SKILLS/$TEST_SKILL.md" ]; then
    echo -e "  ${GREEN}✓${NC} Test skill created: $TEST_SKILL.md"
else
    echo -e "  ${RED}✗${NC} Failed to create test skill"
    exit 1
fi

# =============================================================================
echo -e "${BLUE}3. Verify Skill Contents${NC}"
# =============================================================================

if grep -q "description: Test skill" "$GLOBAL_SKILLS/$TEST_SKILL.md"; then
    echo -e "  ${GREEN}✓${NC} Skill has correct YAML frontmatter"
else
    echo -e "  ${RED}✗${NC} Skill frontmatter incorrect"
fi

if grep -q "## Trigger" "$GLOBAL_SKILLS/$TEST_SKILL.md"; then
    echo -e "  ${GREEN}✓${NC} Skill has Trigger section"
else
    echo -e "  ${RED}✗${NC} Skill missing Trigger section"
fi

if grep -q "## Solution" "$GLOBAL_SKILLS/$TEST_SKILL.md"; then
    echo -e "  ${GREEN}✓${NC} Skill has Solution section"
else
    echo -e "  ${RED}✗${NC} Skill missing Solution section"
fi

# =============================================================================
echo -e "${BLUE}4. List All Skills${NC}"
# =============================================================================

echo ""
echo "Skills in $GLOBAL_SKILLS:"
echo ""

SKILL_COUNT=0
for skill in "$GLOBAL_SKILLS"/*.md; do
    if [ -f "$skill" ]; then
        NAME=$(basename "$skill" .md)
        DESC=$(grep "^description:" "$skill" 2>/dev/null | cut -d: -f2- | xargs || echo "No description")
        echo -e "  • ${GREEN}$NAME${NC}"
        echo -e "    $DESC"
        SKILL_COUNT=$((SKILL_COUNT + 1))
    fi
done

if [ $SKILL_COUNT -eq 0 ]; then
    echo -e "  ${YELLOW}(no skills found)${NC}"
fi

echo ""
echo -e "Total: ${BLUE}$SKILL_COUNT${NC} skills"

# =============================================================================
echo -e "${BLUE}5. Cleanup Test Skill${NC}"
# =============================================================================

rm -f "$GLOBAL_SKILLS/$TEST_SKILL.md"
echo -e "  ${GREEN}✓${NC} Test skill removed"

# =============================================================================
echo ""
echo -e "${BLUE}━━━ Results ━━━${NC}"
echo ""
# =============================================================================

echo -e "${GREEN}Learning flow is working!${NC}"
echo ""
echo "To save a skill manually:"
echo ""
echo "  cat > ~/.claude/skills/learned/my-fix.md << 'EOF'"
echo "  ---"
echo "  name: my-fix"
echo "  description: How to fix XYZ error"
echo "  ---"
echo "  ## Trigger"
echo "  Error: XYZ"
echo "  ## Solution"
echo "  1. Do this"
echo "  2. Do that"
echo "  EOF"
echo ""
echo "Or use /retrospective in Claude Code to auto-extract skills."
echo ""
