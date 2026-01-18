# Example Workflow: Building UI for Adtech-Proton

**Goal:** Build a UI on top of https://github.com/FikretHassan/adtech-proton using vibecoding-stack

---

## Phase 1: Set Up Project in Codespace

### 1. Create Codespace
```
https://github.com/codespaces/new?repo=StreetsDigital/vibes
```

Wait for auto-setup (2 minutes)

### 2. Create Isolated Project
```bash
# Create project for adtech UI
vibecode new adtech-ui javascript

# Enter the project
vibecode shell adtech-ui
```

### 3. Clone Adtech-Proton
```bash
cd /workspace

# Clone the base framework
git clone https://github.com/FikretHassan/adtech-proton.git

# Set up your UI project structure
mkdir -p adtech-admin-ui
cd adtech-admin-ui

# Initialize your UI project
npm init -y
git init
```

---

## Phase 2: Initialize Planning Files

### Create Feature Spec
```bash
# Still in: /workspace/adtech-admin-ui

# Initialize planning files
~/autocoder/scripts/init-session.sh
```

This creates:
- `task_plan.md` - Your goals and phases
- `findings.md` - Technical discoveries
- `progress.md` - What you've done

### Edit `task_plan.md`
```markdown
# Task Plan: Adtech-Proton Admin UI

## Goal
Build a React-based admin UI for configuring and managing adtech-proton framework

## Phases

### Phase 1: Discovery & Setup
- [ ] Explore adtech-proton codebase structure
- [ ] Understand configuration schema
- [ ] Identify what needs UI management
- [ ] Set up React + TypeScript project
- **Status:** in_progress

### Phase 2: Core UI Components
- [ ] Property management interface
- [ ] Partner configuration UI
- [ ] Ad slot configuration
- [ ] Targeting & sizemapping editor
- **Status:** pending

### Phase 3: Configuration Import/Export
- [ ] JSON config viewer/editor
- [ ] Validation system
- [ ] Import/export functionality
- **Status:** pending

### Phase 4: Testing & Integration
- [ ] Component tests
- [ ] E2E tests with adtech-proton
- [ ] Documentation
- **Status:** pending

## Success Criteria
- [ ] Can create/edit adtech-proton configs visually
- [ ] Validates configurations before export
- [ ] Integrates seamlessly with adtech-proton
- [ ] Full test coverage
```

---

## Phase 3: Start Claude Code with Effective Prompts

### Launch Claude
```bash
vibecode code adtech-ui
```

---

## Effective Prompt Template

### Initial Discovery Prompt
```
I want to build an admin UI for the adtech-proton framework.

Context:
- Adtech-proton is in: /workspace/adtech-proton/
- It's a TypeScript ad tech orchestration framework
- Uses JSON config files for properties, partners, ad slots
- My UI will be in: /workspace/adtech-admin-ui/

Tasks:
1. Use aleph_search to explore the adtech-proton codebase
2. Find the configuration schema and interfaces
3. Identify what configuration options exist
4. Document findings in findings.md
5. Create initial React + TypeScript setup

Read task_plan.md first to understand the goal.
```

### Why This Works:
✅ **Context:** Claude knows where everything is
✅ **Clear tasks:** Specific actions with tools
✅ **Planning integration:** References task_plan.md
✅ **Documentation:** Updates findings.md

---

## Phase 4: Feature-by-Feature Development

### Use Autocoder Features

Inside Claude Code:

#### 1. Get Next Feature
```
feature_get_next
```

This returns something like:
```json
{
  "id": 1,
  "name": "Property Management UI",
  "description": "Create UI for managing publisher properties",
  "test_cases": [...],
  "status": "in_progress"
}
```

#### 2. Discuss Before Implementation
```
feature_discuss

My UI idea is:
- Dashboard showing all configured properties
- Form to add/edit properties with validation
- Visual representation of partner assignments
- Real-time config preview

Questions:
- Should this be a standalone SPA or embedded?
- What's the best state management approach?
- How should we handle config validation?
```

Claude will surface considerations and ask clarifying questions.

#### 3. Search the Codebase
```
aleph_search("property|config|schema")
```

Finds relevant files in adtech-proton to understand structure.

```
aleph_peek("adtech-proton/src/types/config.ts", 1, 100)
```

Views the configuration types.

#### 4. Implement with Context
```
Now implement the Property Management UI:

1. Create React components in src/components/PropertyManager/
2. Use the config schema from adtech-proton/src/types/config.ts
3. Add form validation based on the schema
4. Include tests for all components
5. Update progress.md as you go

Follow the patterns from task_plan.md Phase 2.
```

#### 5. Quality Check
```
quality_check(quick=True)
```

Runs lint, types, format checks.

#### 6. Mark Complete
```
feature_mark_passing(1)
```

Only when tests pass and quality gates succeed.

---

## Effective Prompt Patterns

### Pattern 1: Context + Task + Documentation
```
Context: I'm building [X] on top of [Y] located at [path]
Task: [Specific action with specific tools]
Documentation: Update [findings.md/progress.md]
```

### Pattern 2: Research First
```
Before implementing [feature], let's research:
1. aleph_search("[relevant terms]")
2. aleph_peek the key files
3. Document findings in findings.md
4. Then create implementation plan
```

### Pattern 3: Incremental with Planning
```
According to task_plan.md Phase [N]:

Next steps:
1. [Step 1] - update progress.md when done
2. [Step 2] - run quality_check
3. [Step 3] - document in findings.md

After each step, show me progress before continuing.
```

### Pattern 4: UI-Specific
```
For the [Component Name] UI:

Design requirements from my idea:
- [Visual requirement 1]
- [Interaction requirement 2]
- [Data requirement 3]

Implementation:
1. Create component structure
2. Add TypeScript interfaces from adtech-proton types
3. Implement state management
4. Add tests covering [test cases from feature spec]
5. Run quality_check before marking complete
```

---

## Example Full Session

### Prompt 1: Setup
```
I'm starting work on the adtech-proton admin UI project.

First, let's set up the foundation:

1. Read task_plan.md to understand the goal
2. Use aleph_search to find adtech-proton's config types
3. Create a new React + TypeScript project in /workspace/adtech-admin-ui/
4. Install dependencies: react, typescript, vite, vitest
5. Set up basic project structure:
   - src/components/
   - src/types/
   - src/hooks/
   - tests/
6. Document the adtech-proton config schema in findings.md

Update progress.md after each major step.
```

### Prompt 2: First Feature
```
feature_get_next

Let's implement the first feature.

Before coding:
1. feature_discuss - I want a dashboard that shows:
   - List of all configured properties
   - Status of each property (active/inactive)
   - Quick stats (# partners, # ad slots)
   - "Add Property" button

2. aleph_search("property") to find how properties are defined in adtech-proton

3. Create:
   - PropertyDashboard component
   - PropertyCard component
   - AddPropertyButton component
   - Tests for all components

4. quality_check(quick=True) before marking done

Following task_plan.md Phase 2.
```

### Prompt 3: Iterate
```
The PropertyDashboard looks good. Now let's add the form:

feature_get_next

1. Create PropertyForm component with fields from the config schema
2. Add form validation matching adtech-proton's requirements
3. Implement save functionality that exports valid JSON config
4. Add tests covering:
   - Valid input
   - Invalid input (validation errors)
   - Save success
   - Save failure

Run quality_check() when done.
Update progress.md with what we accomplished.
```

### Prompt 4: Integration
```
Now let's integrate with the actual adtech-proton config:

1. aleph_search("config|load|init") to find how adtech-proton loads config
2. Create a config loader utility that:
   - Reads existing adtech-proton configs
   - Validates them
   - Allows editing via our UI
   - Exports back to valid format

3. Add integration tests
4. Update findings.md with how the integration works

Then feature_mark_passing() if all tests pass.
```

---

## Key Tools to Use

| Tool | When to Use | Example |
|------|-------------|---------|
| `feature_get_next` | Start new feature | Get next task from queue |
| `feature_discuss` | Before implementing | Clarify approach, surface issues |
| `aleph_search` | Need to understand code | Search adtech-proton codebase |
| `aleph_peek` | View specific file | See config types, interfaces |
| `quality_check` | After changes | Verify lint, tests, types |
| `feature_mark_passing` | Feature complete | Mark done, auto-runs quality |

---

## Pro Tips

### 1. Always Start with Planning
```
Read task_plan.md
Check progress.md to see what's done
Use feature_discuss before coding
```

### 2. Search Before Creating
```
aleph_search to find existing patterns
Don't reinvent what adtech-proton already has
```

### 3. Incremental Development
```
Small features → quality_check → mark_passing → next feature
Not: everything at once → debug hell
```

### 4. Document as You Go
```
Update findings.md when you discover something
Update progress.md after each action
Claude can reference these later
```

### 5. Quality Gates Always
```
quality_check(quick=True) - after each edit
quality_check() - before marking feature complete
Never skip for UI code
```

---

## Your UI Idea - How to Prompt

When you have a UI idea, structure it like this:

```
I have a UI idea for [feature name].

Vision:
[Describe the visual layout and user flow]

Components needed:
- [Component 1] - does [X]
- [Component 2] - does [Y]

Data requirements:
- Needs data from: [source]
- User inputs: [fields]
- Validation rules: [rules from adtech-proton]

Implementation plan:
1. aleph_search to find relevant types
2. Create components with TypeScript interfaces
3. Add state management for [state description]
4. Implement with tests
5. quality_check before done

Questions to discuss:
- [Any uncertainties or decisions needed]
```

**Claude will:**
- Search adtech-proton for relevant code
- Propose component architecture
- Identify integration points
- Implement with tests
- Check quality
- Document progress

---

## Summary

**The Vibecoding-Stack Flow:**

1. **Create project:** `vibecode new adtech-ui javascript`
2. **Initialize planning:** Use `task_plan.md`, `findings.md`, `progress.md`
3. **Start Claude:** `vibecode code adtech-ui`
4. **Loop:**
   - `feature_get_next` → Get feature
   - `feature_discuss` → Plan approach
   - `aleph_search` → Research codebase
   - Implement → With tests
   - `quality_check` → Verify
   - `feature_mark_passing` → Complete
   - Repeat

**Effective prompts = Context + Clear Task + Tools + Documentation**

Your adtech UI will be built incrementally, with quality gates, full testing, and zero context loss!

Ready to start? Create your Codespace and begin! 🚀
