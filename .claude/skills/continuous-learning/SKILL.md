# Continuous Learning Skill

Automatically extract and retain knowledge from debugging sessions and problem-solving work.

## Purpose

Instead of starting fresh each session, Claude Code learns from discoveries and saves them as reusable skills. Next time the same issue comes up, the solution is already known.

## Activation

### Automatic
Activates when Claude Code completes debugging tasks involving non-obvious discovery.

### Explicit
- `/retrospective` - Analyze current session for extractable knowledge
- "Extract what we learned as a skill"

## Extraction Triggers

1. **Non-obvious Solutions** - Debugging requiring significant investigation
2. **Project-Specific Patterns** - Undocumented conventions in the codebase
3. **Tool Integration Knowledge** - Implementation methods beyond standard docs
4. **Error Resolution** - Specific errors with non-apparent root causes

## Quality Gates

Before extracting, knowledge must satisfy:

- **Reusable** - Applicable to future tasks
- **Non-trivial** - Required discovery, not just documentation lookup
- **Specific** - Has exact trigger conditions
- **Verified** - Actually works

## Skill Format

Skills are saved as markdown files with YAML frontmatter:

```markdown
---
name: skill-name
description: Precise description optimized for semantic matching
author: claude
version: 1.0.0
---

# Skill Name

## Problem
What issue does this solve?

## Trigger Conditions
- Specific error message
- Specific context
- Specific symptoms

## Solution
Step-by-step fix

## Verification
How to confirm it worked
```

## Storage Locations

- **Project-level**: `.claude/skills/learned/` - Project-specific knowledge
- **User-level**: `~/.claude/skills/learned/` - Cross-project knowledge

## Retrospective Process

When `/retrospective` is invoked:

1. Analyze session for extraction candidates
2. Prioritize high-value knowledge
3. Generate 1-3 skills per session
4. Document creation rationale
5. Save to appropriate location

## Example Skills

### Prisma Connection Pooling

```markdown
---
name: prisma-connection-pool-fix
description: Fix Prisma "Too many connections" error in serverless environments
---

## Trigger
Error: "Too many connections" with Prisma in serverless/edge functions

## Solution
1. Use singleton pattern for PrismaClient
2. Set connection_limit in DATABASE_URL
3. Add `?pgbouncer=true` if using PgBouncer

## Verification
Error stops occurring under concurrent load
```

### TypeScript Circular Dependencies

```markdown
---
name: typescript-circular-dep-fix
description: Resolve TypeScript circular dependency causing undefined imports
---

## Trigger
- Import returns undefined
- Works in some files, not others
- No explicit error, just runtime failure

## Solution
1. Check import order
2. Use type-only imports: `import type { X }`
3. Consider barrel file restructuring

## Verification
Import returns expected value at runtime
```

## Integration with Vibes Stack

This skill works alongside:
- **Aleph** - Search learned skills when exploring codebase
- **Quality Gates** - Validate skills before saving
- **Planning Files** - Document learnings in findings.md

## Research Best Practices

When extracting technology-specific knowledge:
1. Search official documentation
2. Check current best practices (post-2025)
3. Review common issues
4. Include "References" section citing sources

---

> "Agents that persist what they learn do better than agents that start fresh."
> — Based on Voyager, CASCADE, SEAgent research
