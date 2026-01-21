"""
Feature MCP Server with Quality Gates Integration
==================================================

Enhanced version of feature_mcp_integrated.py that adds:
1. Quality gate checks before marking features as complete
2. Verification agent for dual-Claude review
3. Pre-commit and post-implementation checks
4. Gastown integration for git-backed persistence (optional)

Drop this into autocoder's mcp_server/ directory.

Backend modes:
- SQLITE (default): Traditional SQLite-based feature queue
- BEADS: Git-backed Gastown-style persistence (crash-proof)

Set VIBES_USE_BEADS=true to enable git-backed mode.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("[feature_mcp] Warning: MCP SDK not installed")

# SQLAlchemy imports for feature management
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
import random

# Gastown integration for git-backed persistence
try:
    from gastown_integration import (
        BeadFeatureAdapter,
        init_kanban_system,
        get_kanban_tools,
        handle_kanban_tool,
        Mayor,
        BeadStore,
        migrate_feature_to_bead
    )
    GASTOWN_AVAILABLE = True
except ImportError:
    GASTOWN_AVAILABLE = False
    print("[feature_mcp] Note: Gastown integration not available")

# Configuration: Use Beads (git-backed) or SQLite
USE_BEADS = os.getenv("VIBES_USE_BEADS", "false").lower() == "true"

# Import other modules
from aleph_bridge import (
    get_aleph_tools,
    handle_aleph_tool,
    on_session_start,
    on_session_end,
    on_feature_complete
)

from subagent_spawner import (
    get_subagent_tools,
    handle_subagent_tool,
    init_subagent_system
)

from quality_gates import (
    get_quality_tools,
    handle_quality_tool,
    init_quality_gates,
    run_quality_checks,
    verify_feature_implementation,
    QualityGateRunner,
    CheckStatus
)


# =============================================================================
# DATABASE SETUP (Feature Management)
# =============================================================================

Base = declarative_base()


class Feature(Base):
    """Feature model for SQLAlchemy."""
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    test_cases = Column(Text)  # JSON array of test cases
    status = Column(String(50), default="pending")  # pending, in_progress, passing, skipped, needs_review
    priority = Column(Integer, default=0)
    verification_status = Column(String(50), default="pending")  # pending, verified, failed
    verification_notes = Column(Text)
    created_at = Column(String(50))
    updated_at = Column(String(50))


# Global state
_db_session = None
_project_dir: Optional[Path] = None
_quality_runner: Optional[QualityGateRunner] = None
_bead_adapter: Optional["BeadFeatureAdapter"] = None  # Gastown adapter
_use_beads: bool = False  # Runtime flag for backend selection

# =============================================================================
# THINKING PROMPTS - Encourage structured reasoning for new task types
# =============================================================================

THINKING_PROMPT = """
## Thinking Guidance

When encountering a **new task type** or **complex problem**, use structured thinking tools:

1. **Sequential Thinking** (`sequential_thinking` MCP):
   - Use for: step-by-step problem breakdown, planning, revising approaches
   - Ideal for: implementation planning, debugging strategies, architecture decisions

2. **Atom of Thoughts** (`AoT` or `AoT-light` MCP):
   - Use for: decomposing complex problems into independent reasoning units
   - Ideal for: analyzing requirements, verification, hypothesis testing

### When to Think First:
- Creating new MCPs, agents, skills, or hooks
- Implementing features with unclear requirements
- Debugging non-obvious issues
- Making architectural decisions
- Any task requiring multiple approaches or iterations

### Example:
Before implementing a complex feature, use `sequential_thinking` to:
1. Break down the requirements
2. Identify potential approaches
3. Consider edge cases
4. Plan the implementation order
5. Define verification criteria
"""

def add_thinking_hint(result: Dict[str, Any], task_type: str = "feature") -> Dict[str, Any]:
    """Add thinking guidance hint to task results."""
    # Add hint for new features or complex tasks
    if "id" in result or "features" in result:
        result["thinking_hint"] = f"""
Consider using thinking tools before starting:
- `sequential_thinking` for step-by-step planning
- `AoT` for decomposing complex requirements

This helps ensure thorough implementation for: {task_type}
"""
    return result


def init_database(project_dir: str) -> None:
    """Initialize database connection (SQLite or Beads)."""
    global _db_session, _project_dir, _quality_runner, _bead_adapter, _use_beads

    _project_dir = Path(project_dir)
    _use_beads = USE_BEADS and GASTOWN_AVAILABLE

    if _use_beads:
        # Use git-backed Beads (Gastown mode)
        print(f"[feature_mcp] Using git-backed Beads (Gastown mode)")
        _bead_adapter = BeadFeatureAdapter(_project_dir)
        init_kanban_system(str(_project_dir))
    else:
        # Use traditional SQLite
        print(f"[feature_mcp] Using SQLite backend")
        db_path = _project_dir / "features.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        _db_session = Session()

    # Initialize quality runner (used by both backends)
    _quality_runner = QualityGateRunner(_project_dir)


# =============================================================================
# FEATURE MANAGEMENT TOOLS (with Quality Gate Integration)
# =============================================================================

def feature_get_stats() -> Dict[str, Any]:
    """Get feature statistics."""
    # Route to Beads backend if enabled
    if _use_beads and _bead_adapter:
        result = _bead_adapter.get_stats()
        result["backend"] = "beads"
        return result

    # SQLite backend
    if _db_session is None:
        return {"error": "Database not initialized"}

    total = _db_session.query(Feature).count()
    passing = _db_session.query(Feature).filter(Feature.status == "passing").count()
    pending = _db_session.query(Feature).filter(Feature.status == "pending").count()
    in_progress = _db_session.query(Feature).filter(Feature.status == "in_progress").count()
    skipped = _db_session.query(Feature).filter(Feature.status == "skipped").count()
    needs_review = _db_session.query(Feature).filter(Feature.status == "needs_review").count()

    return {
        "total": total,
        "passing": passing,
        "pending": pending,
        "in_progress": in_progress,
        "skipped": skipped,
        "needs_review": needs_review,
        "progress_percent": round((passing / total * 100) if total > 0 else 0, 1),
        "backend": "sqlite"
    }


def feature_get_next() -> Dict[str, Any]:
    """Get the next feature to implement."""
    # Route to Beads backend if enabled
    if _use_beads and _bead_adapter:
        result = _bead_adapter.get_next()
        if "id" in result:
            result["backend"] = "beads"
            # Add thinking hint for new features
            result = add_thinking_hint(result, f"feature: {result.get('name', 'unknown')}")
        return result

    # SQLite backend
    if _db_session is None:
        return {"error": "Database not initialized"}

    # First check for in_progress features
    in_progress = _db_session.query(Feature).filter(
        Feature.status == "in_progress"
    ).first()

    if in_progress:
        return {
            "id": in_progress.id,
            "name": in_progress.name,
            "description": in_progress.description,
            "test_cases": json.loads(in_progress.test_cases) if in_progress.test_cases else [],
            "status": "in_progress",
            "note": "Resuming in-progress feature",
            "backend": "sqlite"
        }

    # Check for features needing review
    needs_review = _db_session.query(Feature).filter(
        Feature.status == "needs_review"
    ).first()

    if needs_review:
        result = {
            "id": needs_review.id,
            "name": needs_review.name,
            "description": needs_review.description,
            "test_cases": json.loads(needs_review.test_cases) if needs_review.test_cases else [],
            "status": "needs_review",
            "verification_notes": needs_review.verification_notes,
            "note": "Feature needs review before marking complete",
            "backend": "sqlite"
        }
        # Add thinking hint for review - use AoT to analyze issues
        result["thinking_hint"] = """
This feature needs review. Consider using `AoT` (Atom of Thoughts) to:
1. Analyze the verification notes systematically
2. Identify root causes of failures
3. Plan fixes with clear verification criteria
"""
        return result

    # Get next pending feature by priority
    next_feature = _db_session.query(Feature).filter(
        Feature.status == "pending"
    ).order_by(Feature.priority.desc(), Feature.id).first()

    if next_feature:
        # Mark as in_progress
        next_feature.status = "in_progress"
        _db_session.commit()

        result = {
            "id": next_feature.id,
            "name": next_feature.name,
            "description": next_feature.description,
            "test_cases": json.loads(next_feature.test_cases) if next_feature.test_cases else [],
            "status": "in_progress",
            "backend": "sqlite"
        }
        # Add thinking hint for new features
        result = add_thinking_hint(result, f"feature: {next_feature.name}")
        return result

    return {"message": "All features complete!", "remaining": 0}


def feature_mark_passing(
    feature_id: Any,  # Can be int (SQLite) or str (Beads)
    skip_verification: bool = False
) -> Dict[str, Any]:
    """
    Mark a feature as passing.

    By default, runs quality checks before marking complete.
    Set skip_verification=True to bypass (not recommended).
    """
    # Run quality checks first (shared by both backends)
    quality_result = None
    if not skip_verification and _quality_runner:
        quality_result = _quality_runner.run_quick_checks()

    # Route to Beads backend if enabled
    if _use_beads and _bead_adapter:
        result = _bead_adapter.mark_passing(
            feature_id,
            skip_verification=skip_verification,
            quality_result=quality_result
        )
        if "success" in result:
            result["backend"] = "beads"
        # Trigger Aleph refresh on success
        if result.get("success") and _project_dir:
            on_feature_complete(str(_project_dir), feature_id)
        return result

    # SQLite backend
    if _db_session is None:
        return {"error": "Database not initialized"}

    feature = _db_session.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        return {"error": f"Feature {feature_id} not found"}

    # Check quality result
    if quality_result and quality_result.get("status") == "failed":
        # Don't mark as passing, set to needs_review
        feature.status = "needs_review"
        feature.verification_status = "failed"
        feature.verification_notes = json.dumps(quality_result)
        _db_session.commit()

        return {
            "success": False,
            "feature_id": feature_id,
            "name": feature.name,
            "new_status": "needs_review",
            "quality_result": quality_result,
            "message": "Quality checks failed. Fix issues before marking complete.",
            "backend": "sqlite"
        }

    # Mark as passing
    feature.status = "passing"
    feature.verification_status = "verified"
    _db_session.commit()

    # Trigger Aleph refresh
    if _project_dir:
        on_feature_complete(str(_project_dir), feature_id)

    stats = feature_get_stats()

    return {
        "success": True,
        "feature_id": feature_id,
        "name": feature.name,
        "new_status": "passing",
        "progress": stats,
        "backend": "sqlite"
    }


def feature_verify(feature_id: int) -> Dict[str, Any]:
    """
    Run full verification on a feature before marking complete.
    
    This runs:
    1. All quality checks (tests, lint, types, format, security, build)
    2. Optionally spawns verification agent for code review
    """
    if _db_session is None:
        return {"error": "Database not initialized"}
    
    feature = _db_session.query(Feature).filter(Feature.id == feature_id).first()
    
    if not feature:
        return {"error": f"Feature {feature_id} not found"}
    
    feature_dict = {
        "id": feature.id,
        "name": feature.name,
        "description": feature.description,
        "test_cases": json.loads(feature.test_cases) if feature.test_cases else []
    }
    
    # Run verification
    result = verify_feature_implementation(feature_dict)
    
    # Update feature status based on result
    if result.get("overall_status") == "passed":
        feature.verification_status = "verified"
    elif result.get("overall_status") in ["failed", "needs_review"]:
        feature.status = "needs_review"
        feature.verification_status = "needs_review"
    
    feature.verification_notes = json.dumps(result)
    _db_session.commit()
    
    return {
        "feature_id": feature_id,
        "feature_name": feature.name,
        "verification": result
    }


def feature_skip(feature_id: Any, reason: str = "") -> Dict[str, Any]:
    """Skip a feature (move to end of queue)."""
    # Route to Beads backend if enabled
    if _use_beads and _bead_adapter:
        result = _bead_adapter.skip(feature_id, reason)
        if "success" in result:
            result["backend"] = "beads"
        return result

    # SQLite backend
    if _db_session is None:
        return {"error": "Database not initialized"}

    feature = _db_session.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        return {"error": f"Feature {feature_id} not found"}

    # Lower priority and reset status
    feature.status = "pending"
    feature.priority = feature.priority - 100  # Move down in queue
    _db_session.commit()

    return {
        "success": True,
        "feature_id": feature_id,
        "name": feature.name,
        "reason": reason,
        "new_priority": feature.priority,
        "backend": "sqlite"
    }


def feature_get_for_regression(count: int = 3) -> Dict[str, Any]:
    """Get random passing features for regression testing."""
    # Route to Beads backend if enabled
    if _use_beads and _bead_adapter:
        result = _bead_adapter.get_for_regression(count)
        result["backend"] = "beads"
        return result

    # SQLite backend
    if _db_session is None:
        return {"error": "Database not initialized"}

    passing_features = _db_session.query(Feature).filter(
        Feature.status == "passing"
    ).all()

    if not passing_features:
        return {"features": [], "message": "No passing features yet"}

    selected = random.sample(passing_features, min(count, len(passing_features)))

    return {
        "features": [
            {
                "id": f.id,
                "name": f.name,
                "test_cases": json.loads(f.test_cases) if f.test_cases else []
            }
            for f in selected
        ],
        "backend": "sqlite"
    }


def feature_create_bulk(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create multiple features at once (used by initializer)."""
    # Route to Beads backend if enabled
    if _use_beads and _bead_adapter:
        result = _bead_adapter.create_bulk(features)
        if "success" in result:
            result["backend"] = "beads"
        return result

    # SQLite backend
    if _db_session is None:
        return {"error": "Database not initialized"}

    created = []
    for i, f in enumerate(features):
        feature = Feature(
            name=f.get("name", f"Feature {i+1}"),
            description=f.get("description", ""),
            test_cases=json.dumps(f.get("test_cases", [])),
            status="pending",
            priority=f.get("priority", len(features) - i)
        )
        _db_session.add(feature)
        created.append(feature.name)

    _db_session.commit()

    return {
        "success": True,
        "created_count": len(created),
        "features": created,
        "backend": "sqlite"
    }


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

def get_feature_tools() -> List[Dict[str, Any]]:
    """Get feature management tool definitions."""
    return [
        {
            "name": "feature_get_stats",
            "description": "Get feature progress statistics (total, passing, pending, needs_review, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "feature_get_next",
            "description": "Get the next feature to implement. Returns feature details and test cases.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "feature_mark_passing",
            "description": "Mark a feature as complete. Runs quality checks first unless skip_verification=True.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "integer",
                        "description": "ID of the feature to mark as passing"
                    },
                    "skip_verification": {
                        "type": "boolean",
                        "description": "Skip quality checks (not recommended)",
                        "default": False
                    }
                },
                "required": ["feature_id"]
            }
        },
        {
            "name": "feature_verify",
            "description": "Run full verification on a feature (tests, lint, types, security, build + agent review).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "integer",
                        "description": "ID of the feature to verify"
                    }
                },
                "required": ["feature_id"]
            }
        },
        {
            "name": "feature_skip",
            "description": "Skip a feature if blocked. Moves it to end of queue.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "integer",
                        "description": "ID of the feature to skip"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why the feature is being skipped"
                    }
                },
                "required": ["feature_id"]
            }
        },
        {
            "name": "feature_get_for_regression",
            "description": "Get random passing features for regression testing.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of features to return",
                        "default": 3
                    }
                }
            }
        },
        {
            "name": "feature_create_bulk",
            "description": "Create multiple features at once (initializer use).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "features": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "test_cases": {"type": "array"},
                                "priority": {"type": "integer"}
                            }
                        },
                        "description": "Array of feature definitions"
                    }
                },
                "required": ["features"]
            }
        }
    ]


def handle_feature_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a feature management tool call."""
    handlers = {
        "feature_get_stats": lambda args: feature_get_stats(),
        "feature_get_next": lambda args: feature_get_next(),
        "feature_mark_passing": lambda args: feature_mark_passing(
            args["feature_id"],
            args.get("skip_verification", False)
        ),
        "feature_verify": lambda args: feature_verify(args["feature_id"]),
        "feature_skip": lambda args: feature_skip(
            args["feature_id"], 
            args.get("reason", "")
        ),
        "feature_get_for_regression": lambda args: feature_get_for_regression(
            args.get("count", 3)
        ),
        "feature_create_bulk": lambda args: feature_create_bulk(args["features"])
    }
    
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"Unknown feature tool: {name}"}
    
    try:
        return handler(arguments)
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# MCP SERVER
# =============================================================================

async def run_mcp_server(project_dir: str):
    """Run the integrated MCP server with quality gates."""
    if not MCP_AVAILABLE:
        print("MCP SDK not available")
        return
    
    # Initialize all systems
    init_database(project_dir)
    on_session_start(project_dir)
    init_subagent_system(project_dir)
    init_quality_gates(project_dir)
    
    # Create server
    server = Server("autocoder-vibecoding-quality")
    
    # Combine all tools
    all_tools = (
        get_feature_tools() +
        get_aleph_tools() +
        get_subagent_tools() +
        get_quality_tools()
    )

    # Add kanban tools if using Beads backend
    if _use_beads and GASTOWN_AVAILABLE:
        all_tools = all_tools + get_kanban_tools()
        print("[feature_mcp] Kanban tools enabled (Beads mode)")
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"]
            )
            for t in all_tools
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        # Route to appropriate handler
        if name.startswith("aleph_"):
            result = handle_aleph_tool(name, arguments)
        elif name.startswith("quality_"):
            result = handle_quality_tool(name, arguments)
        elif name.startswith("kanban_") and _use_beads and GASTOWN_AVAILABLE:
            result = handle_kanban_tool(name, arguments)
        elif name.startswith("feature_") and name not in ["feature_discuss", "feature_assumptions", "feature_research"]:
            result = handle_feature_tool(name, arguments)
        elif name.startswith("subagent_") or name in ["feature_discuss", "feature_assumptions", "feature_research"]:
            result = handle_subagent_tool(name, arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python feature_mcp_quality.py <project_dir>")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    asyncio.run(run_mcp_server(project_dir))
