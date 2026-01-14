---
description: Run quality checks and commit changes with a good message
allowed-tools: Bash(git:*), Bash(npm:*), Bash(npx:*), Read
---

# COMMIT WITH QUALITY CHECKS

Run quick quality checks and commit changes.

## STEP 1: PRE-FLIGHT CHECK

```bash
# Check we're not on main/master
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "⚠️  WARNING: You're on $BRANCH branch"
    echo "Consider creating a feature branch first"
fi

# Check for staged changes
STAGED=$(git diff --cached --name-only)
if [ -z "$STAGED" ]; then
    echo "No staged changes. Staging all changes..."
    git add -A
fi

git status --short
```

## STEP 2: QUICK QUALITY CHECKS

```bash
# Format check
echo "📐 Checking format..."
npx prettier --check . 2>/dev/null || black --check . 2>/dev/null || echo "Format OK or not configured"

# Lint
echo "🔍 Running lint..."
npm run lint --silent 2>/dev/null || ruff check . --quiet 2>/dev/null || echo "Lint OK or not configured"

# Type check
echo "📝 Type checking..."
npx tsc --noEmit 2>/dev/null || mypy . --ignore-missing-imports --no-error-summary 2>/dev/null || echo "Types OK or not configured"
```

## STEP 3: GENERATE COMMIT MESSAGE

Based on the changes, generate a conventional commit message:

```bash
# Get the diff summary
git diff --cached --stat
git diff --cached --name-only
```

### Commit Message Format

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `docs:` Documentation
- `test:` Tests
- `chore:` Maintenance

### Example Messages
- `feat: add user authentication with JWT`
- `fix: handle null pointer in API response`
- `refactor: extract validation logic to utils`

## STEP 4: COMMIT

Generate and execute the commit:

```bash
# The message you generate based on the changes
git commit -m "$COMMIT_MESSAGE"
```

## ARGUMENTS

$ARGUMENTS

If the user provided a message, use it. Otherwise, analyze the changes and generate an appropriate conventional commit message.
