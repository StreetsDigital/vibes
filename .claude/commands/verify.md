---
description: Run quality verification before marking a feature as complete
allowed-tools: Bash(*), Read, Grep, Edit
---

# VERIFY FEATURE IMPLEMENTATION

You are running a verification workflow before marking a feature as complete.

## STEP 1: GET CURRENT CHANGES

First, check what's been modified:

```bash
git status
git diff --stat HEAD~1
```

## STEP 2: RUN QUALITY CHECKS

Run the full quality gate suite:

### Tests
```bash
npm test 2>/dev/null || pytest 2>/dev/null || go test ./... 2>/dev/null || echo "No test runner found"
```

### Lint
```bash
npm run lint 2>/dev/null || ruff check . 2>/dev/null || golangci-lint run 2>/dev/null || echo "No linter found"
```

### Type Check
```bash
npx tsc --noEmit 2>/dev/null || mypy . --ignore-missing-imports 2>/dev/null || go vet ./... 2>/dev/null || echo "No type checker found"
```

### Build
```bash
npm run build 2>/dev/null || python -m build 2>/dev/null || go build ./... 2>/dev/null || echo "No build configured"
```

## STEP 3: REVIEW CHANGES

Look at the actual code changes:

```bash
git diff HEAD~1 --name-only
```

For each changed file, verify:
1. ✅ Does it handle error cases?
2. ✅ Are there appropriate tests?
3. ✅ Is the code readable and maintainable?
4. ✅ Any security concerns?

## STEP 4: OUTPUT RESULT

Based on your checks, output ONE of:

- **VERIFIED**: All checks passed, feature is production-ready
- **NEEDS_FIXES**: List specific issues that need fixing
- **NEEDS_TESTS**: Missing test coverage for specific cases
- **BLOCKED**: Cannot proceed due to critical issue

$ARGUMENTS
