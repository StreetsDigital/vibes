# Vibecoding Stack

> Autocoder + Planning-with-Files + Aleph — A three-layer autonomous coding system for long-running projects.

## The Problem

Building complex applications with AI coding agents hits three walls:

1. **Session continuity** — Agent forgets state between sessions
2. **Goal drift** — After 50+ tool calls, agent forgets original intent
3. **Context overflow** — Growing codebase exceeds context window

## The Solution

Each layer solves one problem:

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIBECODING STACK                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   AUTOCODER (Orchestration)                                     │
│   • Feature queue in SQLite                                     │
│   • Two-agent pattern (initializer → coder)                     │
│   • Persists across sessions                                    │
│                                                                 │
│   PLANNING-WITH-FILES (Working Memory)                          │
│   • task_plan.md → goals, phases, decisions                     │
│   • findings.md → research, discoveries                         │
│   • progress.md → actions, test results                         │
│   • Prevents attention drift                                    │
│                                                                 │
│   ALEPH (Context Management)                                    │
│   • External memory for large codebases                         │
│   • Search/peek without stuffing context                        │
│   • Evidence tracking with citations                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone this repo
git clone https://github.com/your-username/vibecoding-stack.git
cd vibecoding-stack

# Run setup (installs autocoder, planning-with-files, aleph)
chmod +x setup.sh
./setup.sh

# Start coding
cd ~/autocoder
./start.sh
```

## The Loop

```
1. AUTOCODER:    feature_get_next → "Implement user auth"
       │
       ▼
2. PRE-PLANNING: feature_discuss → Surface questions
                 feature_assumptions → Check assumptions
                 feature_research → Get libraries_to_fetch
       │
       ▼
3. CONTEXT7:     resolve-library-id → Find library ID
                 get-library-docs → Fetch current docs
       │
       ▼
4. PLANNING:     Read task_plan.md → "Right, we're building X"
       │
       ▼
5. ALEPH:        aleph_search("auth") → Find existing code
       │
       ▼
6. SUBAGENT:     subagent_spawn(feature, code) → Fresh 200k context
       │
       ▼
7. ALEPH:        aleph_refresh → Index new code
       │
       ▼
8. AUTOCODER:    feature_mark_passing → Next feature
       │
       └──────────► REPEAT
```

## Components

### Autocoder (Orchestration)

From [leonvanzyl/autocoder](https://github.com/leonvanzyl/autocoder):

- **Two-agent pattern**: Initializer creates feature list, coder implements
- **SQLite persistence**: Features survive session restarts
- **MCP tools**: `feature_get_next`, `feature_mark_passing`, `feature_skip`
- **Web UI**: React-based monitoring dashboard

### Planning-with-Files (Working Memory)

From [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files):

- **task_plan.md**: Goals, phases, decisions, errors
- **findings.md**: Research discoveries, technical decisions
- **progress.md**: Action log, test results, evidence trail
- **2-Action Rule**: Update findings.md every 2 research actions

### Aleph (Context Management)

From [Hmbown/aleph](https://github.com/Hmbown/aleph):

- **External memory**: Store codebase outside context window
- **Search tools**: Regex search with surrounding context
- **Peek tools**: View specific line ranges
- **Evidence tracking**: Cite code you're building on

### GSD-Borrowed Features

From [glittercowboy/get-shit-done](https://github.com/glittercowboy/get-shit-done):

- **Subagent Spawning**: Fresh 200k context per feature (prevents quality degradation)
- **Pre-Planning Phase**: Think before coding
  - `feature_discuss` — Surface unclear requirements
  - `feature_assumptions` — See what Claude assumes (correct before implementing)
  - `feature_research` — Deep dive for unfamiliar APIs/integrations

### Context7 (Library Documentation)

From [upstash/context7](https://github.com/upstash/context7):

- **Up-to-date docs**: Fetches current, version-specific library documentation
- **No hallucinated APIs**: Based on actual docs, not training data
- **Version-aware**: Specify exact library version for accurate examples
- Tools:
  - `resolve-library-id` — Get Context7 ID for a library name
  - `get-library-docs` — Fetch documentation for specific topics

### Context7 (Up-to-date Documentation)

From [upstash/context7](https://github.com/upstash/context7):

- **Live library docs**: Fetches current, version-specific documentation
- **No outdated APIs**: Docs pulled directly from source, not training data
- **Integrated with pre-planning**: `feature_research` returns libraries to fetch
- **Two tools**:
  - `resolve-library-id` — Find Context7 ID for a library name
  - `get-library-docs` — Fetch current docs for a library

## Integration: aleph_bridge.py

The `aleph_bridge.py` module wires Aleph into autocoder's MCP server:

```python
# Session start
aleph_init(project_dir="/path/to/project")

# Find existing code
aleph_search("auth|login|session")

# View specific lines
aleph_peek("src/auth.ts", start_line=45, end_line=80)

# Record what you're building on
aleph_cite("src/auth.ts", 45, 80, "Auth flow I'm extending")

# After completing a feature
aleph_refresh()  # Re-index the codebase
```

## Tools Reference

### Feature Tools (Autocoder)

| Tool | Description |
|------|-------------|
| `feature_get_stats` | Progress statistics |
| `feature_get_next` | Get next feature to implement |
| `feature_mark_passing` | Complete a feature |
| `feature_skip` | Skip if blocked |
| `feature_get_for_regression` | Random passing features for testing |

### Pre-Planning Tools (from GSD)

| Tool | Description |
|------|-------------|
| `feature_discuss` | Surface questions, edge cases, dependencies |
| `feature_assumptions` | See what Claude assumes — correct before coding |
| `feature_research` | Deep dive for unfamiliar APIs/domains |

### Subagent Tools (from GSD)

| Tool | Description |
|------|-------------|
| `subagent_spawn` | Fresh 200k context for feature implementation |

### Context7 Tools (up-to-date docs)

| Tool | Description |
|------|-------------|
| `resolve-library-id` | Find Context7 ID for a library name |
| `get-library-docs` | Fetch current docs for a library (with optional topic) |

### Aleph Tools

| Tool | Description |
|------|-------------|
| `aleph_init` | Initialize at session start |
| `aleph_search` | Regex search codebase |
| `aleph_peek` | View specific lines |
| `aleph_list_files` | See indexed files |
| `aleph_cite` | Record code reference |
| `aleph_evidence` | Get citation trail |
| `aleph_refresh` | Re-index after changes |
| `aleph_search_planning` | Search planning files |

## When to Use Each Layer

| Situation | Layer | Action |
|-----------|-------|--------|
| "What's next?" | Autocoder | `feature_get_next` |
| "What questions should I ask?" | Pre-Planning | `feature_discuss` |
| "What am I assuming?" | Pre-Planning | `feature_assumptions` |
| "What libraries do I need docs for?" | Pre-Planning | `feature_research` |
| "How does this library work?" | Context7 | `resolve-library-id` + `get-library-docs` |
| "What's my goal?" | Planning | Read `task_plan.md` |
| "Where's the auth code?" | Aleph | `aleph_search("auth")` |
| "Complex feature, need fresh context" | Subagent | `subagent_spawn` |
| "Feature done" | Autocoder | `feature_mark_passing` |
| "Re-index code" | Aleph | `aleph_refresh` |

## File Structure

```
vibecoding-stack/
├── setup.sh                 # Installation script
├── CLAUDE.md                # Agent instructions
├── README.md                # This file
├── scripts/
│   └── init-session.sh      # Initialize planning files
└── mcp_server/
    ├── aleph_bridge.py      # Aleph integration module
    ├── subagent_spawner.py  # GSD-style subagent spawning
    └── feature_mcp_integrated.py  # Combined MCP server

After setup, in ~/autocoder:
├── mcp_server/
│   ├── aleph_bridge.py      # Copied here
│   ├── subagent_spawner.py  # Copied here
│   └── feature_mcp_integrated.py
├── CLAUDE.md                # Copied here
└── ... (autocoder files)
```

## Configuration

### Environment Variables

```bash
# For Aleph sub_query (recursive decomposition)
export OPENAI_API_KEY=...
export ALEPH_SUB_QUERY_MODEL=gpt-4o-mini

# Project directory
export AUTOCODER_DIR=$HOME/autocoder
```

### Claude Desktop Config

The setup script adds this to `~/.config/claude-desktop/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vibecoding": {
      "command": "python3",
      "args": ["/path/to/autocoder/mcp_server/feature_mcp_integrated.py"]
    }
  }
}
```

## Troubleshooting

### "Aleph not installed"

```bash
pip install aleph-rlm[mcp]
# or from source:
pip install git+https://github.com/Hmbown/aleph.git#egg=aleph-rlm[mcp]
```

### "Planning files not found"

```bash
# In your project directory:
cp ~/.claude/skills/planning-with-files/templates/*.md .
```

### "Feature database missing"

```bash
# The initializer agent creates this on first run
# Or manually:
python -c "from feature_mcp_integrated import init_database; init_database('.')"
```

### "Context window still filling up"

- Check `aleph_list_files` — are large files being indexed?
- Adjust `max_file_size_kb` in `AlephBridgeConfig`
- Use `aleph_search` instead of `cat` for exploration

## Credits

- **Autocoder**: [leonvanzyl/autocoder](https://github.com/leonvanzyl/autocoder)
- **Planning-with-Files**: [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files)
- **Aleph**: [Hmbown/aleph](https://github.com/Hmbown/aleph)
- **Get Shit Done**: [glittercowboy/get-shit-done](https://github.com/glittercowboy/get-shit-done) (subagent spawning & pre-planning)
- **Context7**: [upstash/context7](https://github.com/upstash/context7) (up-to-date library documentation)

## License

MIT — See individual repos for component licenses.
