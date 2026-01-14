"""
Feature MCP Server with Quality Gates Integration
==================================================

Enhanced version of feature_mcp_integrated.py that adds:
1. Quality gate checks before marking features as complete
2. Verification agent for dual-Claude review
3. Pre-commit and post-implementation checks

Drop this into autocoder's mcp_server/ directory.
"""

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


def init_database(project_dir: str) -> None:
    """Initialize database connection."""
    global _db_session, _project_dir, _quality_runner
    
    _project_dir = Path(project_dir)
    db_path = _project_dir / "features.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    _db_session = Session()
    
    # Initialize quality runner
    _quality_runner = QualityGateRunner(_project_dir)


# =============================================================================
# FEATURE MANAGEMENT TOOLS (with Quality Gate Integration)
# =============================================================================

def feature_get_stats() -> Dict[str, Any]:
    """Get feature statistics."""
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
        "progress_percent": round((passing / total * 100) if total > 0 else 0, 1)
    }


def feature_get_next() -> Dict[str, Any]:
    """Get the next feature to implement."""
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
            "note": "Resuming in-progress feature"
        }
    
    # Check for features needing review
    needs_review = _db_session.query(Feature).filter(
        Feature.status == "needs_review"
    ).first()
    
    if needs_review:
        return {
            "id": needs_review.id,
            "name": needs_review.name,
            "description": needs_review.description,
            "test_cases": json.loads(needs_review.test_cases) if needs_review.test_cases else [],
            "status": "needs_review",
            "verification_notes": needs_review.verification_notes,
            "note": "Feature needs review before marking complete"
        }
    
    # Get next pending feature by priority
    next_feature = _db_session.query(Feature).filter(
        Feature.status == "pending"
    ).order_by(Feature.priority.desc(), Feature.id).first()
    
    if next_feature:
        # Mark as in_progress
        next_feature.status = "in_progress"
        _db_session.commit()
        
        return {
            "id": next_feature.id,
            "name": next_feature.name,
            "description": next_feature.description,
            "test_cases": json.loads(next_feature.test_cases) if next_feature.test_cases else [],
            "status": "in_progress"
        }
    
    return {"message": "All features complete!", "remaining": 0}


def feature_mark_passing(
    feature_id: int, 
    skip_verification: bool = False
) -> Dict[str, Any]:
    """
    Mark a feature as passing.
    
    By default, runs quality checks before marking complete.
    Set skip_verification=True to bypass (not recommended).
    """
    if _db_session is None:
        return {"error": "Database not initialized"}
    
    feature = _db_session.query(Feature).filter(Feature.id == feature_id).first()
    
    if not feature:
        return {"error": f"Feature {feature_id} not found"}
    
    # Run quality checks unless skipped
    if not skip_verification and _quality_runner:
        quality_result = _quality_runner.run_quick_checks()
        
        if quality_result.get("status") == "failed":
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
                "message": "Quality checks failed. Fix issues before marking complete."
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
        "progress": stats
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


def feature_skip(feature_id: int, reason: str = "") -> Dict[str, Any]:
    """Skip a feature (move to end of queue)."""
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
        "new_priority": feature.priority
    }


def feature_get_for_regression(count: int = 3) -> Dict[str, Any]:
    """Get random passing features for regression testing."""
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
        ]
    }


def feature_create_bulk(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create multiple features at once (used by initializer)."""
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
        "features": created
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
