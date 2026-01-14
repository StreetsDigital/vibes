# Vibecoding Stack

Autonomous coding with quality gates: Autocoder + Planning Files + Aleph + Quality Gates

## Quick Start

```bash
chmod +x setup.sh && ./setup.sh
```

## Structure

```
mcp_server/
├── vibecoding_server.py   # Combined MCP server
├── aleph_bridge.py        # Codebase search
├── subagent_spawner.py    # Fresh context
└── quality_gates.py       # Tests/lint/types

.claude/
├── settings.json          # Permissions
└── commands/              # /verify, /commit
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "vibecoding": {
      "command": "python3",
      "args": ["~/Desktop/vibecoding-stack/mcp_server/vibecoding_server.py", "."]
    }
  }
}
```

## The Loop

1. `feature_get_next` → Get feature
2. `feature_discuss` → Think first
3. `aleph_search` → Find code
4. Implement → Write code + tests
5. `quality_check` → Verify
6. `feature_mark_passing` → Complete
7. Repeat

## Tools

| Category | Tools |
|----------|-------|
| Features | `feature_get_next`, `feature_mark_passing`, `feature_skip` |
| Planning | `feature_discuss`, `feature_assumptions`, `feature_research` |
| Search | `aleph_search`, `aleph_peek`, `aleph_cite`, `aleph_refresh` |
| Subagent | `subagent_spawn` |
| Quality | `quality_check`, `quality_verify` |
