# CLAUDE.md — Vibecoding Stack with Quality Gates

## Overview

You are operating within a production-ready autonomous coding stack. Every feature you implement goes through quality gates before being marked complete.

| Layer | Purpose | When to Use |
|-------|---------|-------------|
| **Autocoder** | Session orchestration | Always — drives the feature queue |
| **Planning-with-Files** | Goal coherence | Before every major decision |
| **Aleph** | Context management | When codebase > ~5k lines |
| **Quality Gates** | Production readiness | Before marking ANY feature complete |
| **Continuous Learning** | Knowledge retention | After debugging/problem-solving |

---

## The Production-Ready Loop

```
┌─────────────────────────────────────────────────────────────────┐
│  1. GET NEXT FEATURE                                            │
│     └─► feature_get_next → "Implement user authentication"      │
├─────────────────────────────────────────────────────────────────┤
│  2. PRE-PLANNING PHASE                                          │
│     └─► feature_discuss → Surface unclear requirements          │
│     └─► feature_assumptions → See what Claude assumes           │
│     └─► feature_research → Deep dive if needed                  │
├─────────────────────────────────────────────────────────────────┤
│  3. REFRESH CONTEXT (Planning-with-Files)                       │
│     └─► Read task_plan.md — "What's my goal?"                   │
│     └─► Read findings.md — "What have I learned?"               │
│     └─► Read progress.md — "What have I done?"                  │
├─────────────────────────────────────────────────────────────────┤
│  4. EXPLORE CODEBASE (Aleph)                                    │
│     └─► aleph_search("auth|login|session")                      │
│     └─► aleph_peek("src/middleware/auth.ts", 1, 50)             │
│     └─► aleph_cite(...) — record what you're building on        │
├─────────────────────────────────────────────────────────────────┤
│  5. IMPLEMENT FEATURE                                           │
│     └─► Write code following existing patterns                  │
│     └─► Write tests for all test cases in spec                  │
│     └─► Handle error cases and edge cases                       │
├─────────────────────────────────────────────────────────────────┤
│  6. QUALITY VERIFICATION ⬅️ NEW                                  │
│     └─► quality_check(quick=True) → lint, types, format         │
│     └─► quality_check() → full suite including tests            │
│     └─► feature_verify → automated + agent verification         │
├─────────────────────────────────────────────────────────────────┤
│  7. MARK COMPLETE (only if verification passed)                 │
│     └─► feature_mark_passing → auto-runs quality checks         │
│     └─► aleph_refresh → Re-index codebase                       │
│     └─► /commit → Commit with good message                      │
├─────────────────────────────────────────────────────────────────┤
│  8. LEARN (after significant debugging)                         │
│     └─► /retrospective → Extract reusable knowledge             │
│     └─► Save skills to ~/.claude/skills/learned/                │
│     └─► Document insights in findings.md                        │
├─────────────────────────────────────────────────────────────────┤
│  9. LOOP → Back to step 1                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quality Gates (The Gatekeeper)

### Why Quality Gates?

Without quality gates:
```
Feature 1: "Looks good to me" → merged
Feature 5: "Probably fine" → merged
Feature 10: "I'll add tests later" → merged
Production: 💥
```

With quality gates:
```
Feature 1: Tests ✅ Lint ✅ Types ✅ → merged
Feature 5: Tests ❌ → FIX FIRST
Feature 10: Security ⚠️ → REVIEW FIRST
Production: 🎉
```

### Quality Check Commands

| Command | What It Checks | When to Use |
|---------|---------------|-------------|
| `quality_check(quick=True)` | lint, types, format | After every edit |
| `quality_check()` | tests, lint, types, format, security, build | Before marking complete |
| `feature_verify(id)` | Full suite + agent review | For complex features |
| `/verify` | Slash command for manual check | Anytime |

### The Verification Flow

```python
# BEFORE marking any feature complete, run:
result = quality_check()

if result["status"] == "passed":
    feature_mark_passing(feature_id)  # Safe to proceed
elif result["status"] == "warning":
    # Review warnings, decide if acceptable
    feature_mark_passing(feature_id, skip_verification=True)  # Use carefully
elif result["status"] == "failed":
    # FIX THE ISSUES FIRST
    # Do not mark as passing until fixed
```

### What Each Check Does

| Check | Purpose | Command |
|-------|---------|---------|
| **tests** | Verify functionality works | `npm test` / `pytest` |
| **lint** | Catch code issues | `npm run lint` / `ruff check` |
| **types** | Catch type errors | `tsc --noEmit` / `mypy` |
| **format** | Consistent style | `prettier --check` / `black --check` |
| **security** | Find vulnerabilities | `npm audit` / `bandit` |
| **build** | Verify it compiles | `npm run build` |

### Auto-Fix on Edit (Hooks)

The stack automatically runs after every file edit:
1. **Format** — Prettier/Black auto-formats
2. **Lint** — ESLint/Ruff auto-fixes
3. **Log** — Changes logged for audit

You don't need to manually format — hooks handle it.

---

## Feature Workflow with Quality Gates

### Step 1: Get Feature

```python
feature = feature_get_next()
# Returns: {id: 1, name: "User Auth", test_cases: [...], status: "in_progress"}
```

### Step 2: Pre-Planning

```python
# Surface questions
feature_discuss(feature)

# Check assumptions
feature_assumptions(feature)

# Research if needed
feature_research(feature, topics=["JWT", "bcrypt"])
```

### Step 3: Implement

Write the code, following patterns from:
- `aleph_search` results
- `findings.md` discoveries
- `task_plan.md` decisions

**CRITICAL: Write tests for EVERY test case in the feature spec.**

### Step 4: Quick Check (After Implementation)

```python
# Run quick checks
result = quality_check(quick=True)

if result["status"] != "passed":
    # Fix issues before proceeding
    print(result["checks"])  # See what failed
```

### Step 5: Full Verification

```python
# Run full quality gate
result = quality_check()

# Or run with agent verification
result = feature_verify(feature["id"])
```

### Step 6: Mark Complete (Only if Passed)

```python
# This auto-runs quality checks
result = feature_mark_passing(feature["id"])

if result["success"]:
    # Feature is complete, index updated
    pass
else:
    # Quality check failed, feature set to "needs_review"
    print(result["quality_result"])
```

### Step 7: Commit

```bash
git add -A
git commit -m "feat: implement user authentication"
# Pre-commit hook runs quick checks automatically
```

---

## Quality Gate Rules

### ❌ NEVER Skip Verification For:

1. **Security-related features** (auth, payments, data handling)
2. **Public-facing APIs**
3. **Database migrations**
4. **Features touching user data**

### ⚠️ May Skip with Caution For:

1. Documentation updates
2. Config file changes
3. Minor UI tweaks

### How to Skip (When Justified)

```python
# Only when you've manually verified
feature_mark_passing(feature_id, skip_verification=True)
```

---

## Pre-Commit Hooks

The stack includes git hooks that run automatically:

### On Commit
- ✅ Secrets detection (blocks if found)
- ✅ Format check (can auto-fix)
- ✅ Lint check
- ✅ Type check

### On Push
- ✅ Full test suite
- ✅ Build verification

### Installing Hooks

```bash
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## CI/CD Integration

The GitHub Actions workflow runs on every PR:

| Job | What It Checks | Blocks Merge? |
|-----|---------------|---------------|
| `quick-checks` | lint, types, format | Yes |
| `tests` | full test suite + coverage | Yes |
| `security` | npm audit, bandit, CodeQL | No (warnings) |
| `ai-review` | Claude Code reviews PR | No (advisory) |
| `build` | verifies build succeeds | Yes |

### Quality Gate Summary

PRs must pass:
1. ✅ Quick checks (lint, types, format)
2. ✅ Tests
3. ✅ Build

Before merging.

---

## Dual-Agent Verification

For critical features, use dual-agent verification:

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   AGENT 1 (Implementer)                                        │
│   └─► Writes the feature code                                  │
│   └─► Writes tests                                             │
│   └─► Runs quality_check()                                     │
│                                                                │
│   ↓ Output                                                     │
│                                                                │
│   AGENT 2 (Verifier)                                           │
│   └─► Reviews code for logic errors                            │
│   └─► Checks edge cases                                        │
│   └─► Verifies security                                        │
│   └─► Returns: VERIFIED or ISSUES_FOUND                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Trigger Dual-Agent Verification

```python
# For critical features
result = feature_verify(feature_id)

# Result includes:
# - automated_checks: tests, lint, etc.
# - agent_verification: second Claude's review
# - overall_status: passed/needs_review/failed
```

---

## Quick Reference

### Quality Commands

```python
# Quick checks (lint, types, format)
quality_check(quick=True)

# Full checks (all)
quality_check()

# Specific checks
quality_check(checks=["tests", "lint"])

# Full verification with agent
feature_verify(feature_id)
```

### Feature Commands with Quality

```python
# Get next (includes needs_review features)
feature_get_next()

# Mark complete (auto-runs quality checks)
feature_mark_passing(id)

# Mark complete (skip checks - use rarely)
feature_mark_passing(id, skip_verification=True)

# Explicit verification
feature_verify(id)
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/verify` | Run quality verification |
| `/commit` | Commit with quality checks |
| `/retrospective` | Extract learnings as reusable skills |

---

## Continuous Learning

After debugging sessions or solving non-obvious problems, extract knowledge for future use.

### When to Extract

- Non-obvious solutions requiring significant investigation
- Project-specific patterns not in documentation
- Tool integration knowledge beyond standard docs
- Error resolution with non-apparent root causes

### How to Extract

```bash
# At end of session with debugging work
/retrospective
```

This analyzes the session and creates 1-3 skills.

### Skill Format

```markdown
---
name: fix-prisma-connections
description: Fix "Too many connections" error in serverless
author: claude
version: 1.0.0
---

## Trigger
Error: "Too many connections" with Prisma in serverless

## Solution
1. Use singleton pattern for PrismaClient
2. Set connection_limit in DATABASE_URL

## Verification
Error stops occurring under concurrent load
```

### Storage Locations

| Location | Purpose |
|----------|---------|
| `.claude/skills/learned/` | Project-specific knowledge |
| `~/.claude/skills/learned/` | Cross-project knowledge |

### Quality Gates for Skills

Only extract if:
- Would save time if encountered again
- Not easily found in documentation
- Has specific, recognizable trigger
- Solution is verified to work

---

## Troubleshooting

### "Quality check failed"

1. Run `quality_check()` to see what failed
2. Look at the `details` field for specific errors
3. Fix the issues
4. Run again

### "Tests failing"

1. Run `npm test` or `pytest` directly
2. Check test output for failures
3. Fix failing tests
4. Ensure new code has tests

### "Lint errors"

1. Run `npm run lint:fix` or `ruff --fix`
2. Most issues auto-fix
3. Manual fixes for complex issues

### "Type errors"

1. Run `npx tsc --noEmit` or `mypy .`
2. Fix type annotations
3. Add type definitions if missing

### "Security vulnerabilities"

1. Run `npm audit` or `bandit -r .`
2. Update vulnerable dependencies
3. Or add to ignore list if false positive

---

## The Golden Rule

> **No feature is complete until it passes quality gates.**

This means:
- ✅ Tests pass
- ✅ Lint passes
- ✅ Types pass
- ✅ Build passes
- ✅ No critical security issues

Only then: `feature_mark_passing()`

---

## Checklist for Every Feature

Before marking any feature complete:

```markdown
## Pre-Completion Checklist

- [ ] All test cases from spec are covered
- [ ] Tests pass (`npm test` / `pytest`)
- [ ] Lint passes (`npm run lint`)
- [ ] Types pass (`tsc --noEmit` / `mypy`)
- [ ] No hardcoded secrets
- [ ] Error handling complete
- [ ] Edge cases handled
- [ ] quality_check() returns "passed"
```

Copy this into progress.md for each feature.
