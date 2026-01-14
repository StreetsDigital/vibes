#!/usr/bin/env bash
#
# Initialize Planning Files for Vibecoding Stack
# ==============================================
#
# Creates task_plan.md, findings.md, and progress.md
# in the current project directory.
#

set -e

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Initializing planning files...${NC}"

# Create task_plan.md
if [ ! -f "task_plan.md" ]; then
    cat > task_plan.md << 'EOF'
# Task Plan

## Goal
[Describe the main objective of this project/task]

## Phases

### Phase 1: Setup & Discovery
- [ ] Understand requirements
- [ ] Research existing solutions
- [ ] Set up development environment
- **Status:** pending

### Phase 2: Core Implementation
- [ ] Implement main features
- [ ] Write unit tests
- **Status:** pending

### Phase 3: Integration & Testing
- [ ] Integration testing
- [ ] Bug fixes
- **Status:** pending

### Phase 4: Polish & Delivery
- [ ] Documentation
- [ ] Final review
- **Status:** pending

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| | | |

## Errors Encountered

| Error | Resolution | Date |
|-------|------------|------|
| | | |

## Constraints
- [List any constraints or requirements]

## Success Criteria
- [ ] [Define what "done" looks like]

---
*Read this file before every major decision to stay aligned with goals.*
EOF
    echo -e "${GREEN}✓${NC} Created task_plan.md"
else
    echo "  task_plan.md already exists"
fi

# Create findings.md
if [ ! -f "findings.md" ]; then
    cat > findings.md << 'EOF'
# Findings

## Technical Discoveries

### Architecture
- [Document how the system is structured]

### Patterns Found
- [Document patterns discovered in the codebase]

### Dependencies
- [List key dependencies and their purposes]

## Research Notes

### Approaches Considered
| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| | | | |

### Resources
- [Useful URLs, documentation, etc.]

## Technical Decisions

| Decision | Context | Rationale | Date |
|----------|---------|-----------|------|
| | | | |

## Code Patterns

### Naming Conventions
- [Document naming patterns]

### File Organization
- [Document file structure patterns]

### Testing Patterns
- [Document how tests are structured]

---
*Update this file every 2 research/exploration actions.*
EOF
    echo -e "${GREEN}✓${NC} Created findings.md"
else
    echo "  findings.md already exists"
fi

# Create progress.md
if [ ! -f "progress.md" ]; then
    cat > progress.md << 'EOF'
# Progress Log

## Current Session

### Session Start
- **Date:** [YYYY-MM-DD HH:MM]
- **Phase:** [Current phase from task_plan.md]
- **Focus:** [What this session is working on]

### Actions Taken
1. [Action 1]
2. [Action 2]

### Files Modified
- [file1.ts] (created/modified/deleted)
- [file2.ts] (created/modified/deleted)

### Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| | | | | |

### Blockers
- [Any blockers encountered]

---

## 5-Question Reboot Check

Use this when resuming after a break or context refresh:

| Question | Answer |
|----------|--------|
| Where am I? | [Current phase] |
| Where am I going? | [Next phases] |
| What's the goal? | [From task_plan.md] |
| What have I learned? | [Key findings] |
| What have I done? | [Recent actions] |

---

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| | | 1 | |

---

## Evidence Trail

[Citations from aleph_cite will be appended here]

---
*Update after every action. This is your proof of work.*
EOF
    echo -e "${GREEN}✓${NC} Created progress.md"
else
    echo "  progress.md already exists"
fi

echo ""
echo -e "${GREEN}Planning files initialized!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit task_plan.md to define your goal"
echo "  2. Run your autocoder session"
echo "  3. The agent will maintain these files as it works"
echo ""
