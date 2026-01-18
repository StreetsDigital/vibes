# Codex Review

Run OpenAI-powered code review to find bugs and issues.

## Usage

```
/codex-review [files...]
```

If no files specified, analyzes recent git changes.

## Process

1. Collect code from specified files or recent git changes
2. Send to OpenAI GPT-4 for analysis
3. Return structured list of issues with:
   - File and line number
   - Severity (critical/high/medium/low)
   - Issue type (bug/security/performance/logic)
   - Description and suggested fix

## Instructions

When this skill is invoked:

1. Run the codex review script:
   ```bash
   python3 scripts/codex-review.py $ARGUMENTS
   ```

2. Parse the JSON output from the script

3. For each issue found, add it to the todo list using TodoWrite with:
   - Priority based on severity (critical/high first)
   - Clear description of what needs fixing
   - The suggested fix approach

4. Report summary to user:
   - Number of issues found by severity
   - Files affected
   - Offer to start fixing issues

## Example Output

```
🔍 Found 3 issues:

1. 🔴 [CRITICAL] src/auth.py:45
   Type: security
   Issue: SQL injection vulnerability in user query
   Fix: Use parameterized queries

2. 🟠 [HIGH] src/api.py:122
   Type: bug
   Issue: Uncaught exception when API returns null
   Fix: Add null check before accessing response.data

3. 🟡 [MEDIUM] src/utils.py:89
   Type: performance
   Issue: N+1 query in loop
   Fix: Batch database queries outside loop
```

## Environment

Requires `OPENAI_API_KEY` environment variable or key stored in `~/.config/openai/api_key`
