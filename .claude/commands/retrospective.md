# /retrospective - Extract Learnings from Session

Analyze the current session for extractable knowledge and create reusable skills.

## Process

1. **Review the session** for debugging discoveries, non-obvious solutions, and project-specific patterns

2. **Identify candidates** that meet quality gates:
   - Reusable across future tasks
   - Non-trivial (required discovery, not documentation lookup)
   - Specific trigger conditions
   - Verified to work

3. **For each candidate**, create a skill file:

```markdown
---
name: descriptive-skill-name
description: Precise description optimized for semantic matching
author: claude
version: 1.0.0
---

# Skill Name

## Problem
What issue does this solve?

## Trigger Conditions
- Specific error message or symptom
- Context where this applies

## Solution
Step-by-step fix

## Verification
How to confirm it worked

## References
- Sources consulted
```

4. **Save skills** to appropriate location:
   - Project-specific: `.claude/skills/learned/`
   - Cross-project: `~/.claude/skills/learned/`

5. **Document** in `findings.md` what was learned

## Quality Gates

Only extract if:
- [ ] Would save time if encountered again
- [ ] Not easily found in documentation
- [ ] Has specific, recognizable trigger
- [ ] Solution is verified to work

## Output

Generate 1-3 skills maximum per session. Quality over quantity.

After extraction, summarize:
- What skills were created
- Why they were valuable
- Where they were saved
