"""
Aleph Bridge for Autocoder
==========================

Integrates Aleph (recursive LLM reasoning) into autocoder's MCP server.
Provides tools for:
1. Indexing the growing codebase into Aleph's external memory
2. Searching/navigating code without stuffing context window
3. Chunked processing for large file operations

Usage:
    This module exposes MCP tools that the Claude agent can call.
    It bridges autocoder's feature-driven workflow with Aleph's
    context management capabilities.
"""

import os
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from functools import lru_cache

# Try to import Aleph - graceful fallback if not installed
try:
    from aleph import AlephContext, search, peek, chunk, cite
    ALEPH_AVAILABLE = True
except ImportError:
    ALEPH_AVAILABLE = False
    print("[aleph_bridge] Warning: aleph-rlm not installed. Install with: pip install aleph-rlm[mcp]")


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class AlephBridgeConfig:
    """Configuration for the Aleph bridge."""
    
    # File patterns to index
    include_patterns: List[str] = field(default_factory=lambda: [
        "*.py", "*.js", "*.ts", "*.tsx", "*.jsx",
        "*.go", "*.rs", "*.java", "*.kt",
        "*.css", "*.scss", "*.html", "*.vue", "*.svelte",
        "*.json", "*.yaml", "*.yml", "*.toml",
        "*.md", "*.txt", "*.sh", "*.bat",
        "Dockerfile", "Makefile", "*.sql"
    ])
    
    # Directories to skip
    exclude_dirs: List[str] = field(default_factory=lambda: [
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "coverage",
        ".pytest_cache", ".mypy_cache", "egg-info"
    ])
    
    # Size thresholds
    max_file_size_kb: int = 500  # Skip files larger than this
    context_refresh_threshold_kb: int = 50  # Re-index if codebase grew by this much
    
    # Chunk settings for large operations
    default_chunk_size: int = 100_000  # ~100k chars per chunk
    overlap_chars: int = 500  # Overlap between chunks for continuity


# =============================================================================
# CODEBASE INDEXER
# =============================================================================

class CodebaseIndexer:
    """
    Indexes the project codebase into Aleph's external memory.
    Tracks changes to avoid redundant re-indexing.
    """
    
    def __init__(self, project_dir: Path, config: Optional[AlephBridgeConfig] = None):
        self.project_dir = Path(project_dir)
        self.config = config or AlephBridgeConfig()
        self._last_index_hash: Optional[str] = None
        self._last_index_size: int = 0
        self._indexed_files: Dict[str, str] = {}  # path -> content hash
        
    def _should_include_file(self, file_path: Path) -> bool:
        """Check if file should be included in index."""
        # Check exclusions
        for exclude in self.config.exclude_dirs:
            if exclude in file_path.parts:
                return False
        
        # Check size
        try:
            size_kb = file_path.stat().st_size / 1024
            if size_kb > self.config.max_file_size_kb:
                return False
        except OSError:
            return False
            
        # Check patterns
        name = file_path.name
        for pattern in self.config.include_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
                
        return False
    
    def _collect_files(self) -> Dict[str, str]:
        """Collect all indexable files and their contents."""
        files = {}
        
        for file_path in self.project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if not self._should_include_file(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                rel_path = str(file_path.relative_to(self.project_dir))
                files[rel_path] = content
            except Exception as e:
                print(f"[aleph_bridge] Warning: Could not read {file_path}: {e}")
                
        return files
    
    def _compute_hash(self, files: Dict[str, str]) -> str:
        """Compute hash of all file contents for change detection."""
        hasher = hashlib.sha256()
        for path in sorted(files.keys()):
            hasher.update(path.encode())
            hasher.update(files[path].encode())
        return hasher.hexdigest()[:16]
    
    def needs_reindex(self) -> bool:
        """Check if codebase has changed enough to warrant re-indexing."""
        files = self._collect_files()
        current_hash = self._compute_hash(files)
        
        if current_hash != self._last_index_hash:
            # Calculate size change
            current_size = sum(len(c) for c in files.values())
            size_change_kb = abs(current_size - self._last_index_size) / 1024
            
            # Always re-index if hash changed and size grew significantly
            if size_change_kb >= self.config.context_refresh_threshold_kb:
                return True
            # Or if this is first index
            if self._last_index_hash is None:
                return True
                
        return False
    
    def build_context(self) -> str:
        """
        Build a single context string from all indexed files.
        Format designed for Aleph's search capabilities.
        """
        files = self._collect_files()
        
        # Update tracking
        self._last_index_hash = self._compute_hash(files)
        self._last_index_size = sum(len(c) for c in files.values())
        self._indexed_files = {p: hashlib.sha256(c.encode()).hexdigest()[:8] 
                               for p, c in files.items()}
        
        # Build context with file markers
        parts = []
        parts.append("=" * 80)
        parts.append("CODEBASE INDEX")
        parts.append(f"Generated: {datetime.now().isoformat()}")
        parts.append(f"Files: {len(files)}")
        parts.append(f"Total size: {self._last_index_size:,} chars")
        parts.append("=" * 80)
        parts.append("")
        
        # Table of contents
        parts.append("## FILE INDEX")
        parts.append("")
        for i, path in enumerate(sorted(files.keys()), 1):
            parts.append(f"{i:4d}. {path}")
        parts.append("")
        parts.append("=" * 80)
        parts.append("")
        
        # File contents with clear delimiters
        for path in sorted(files.keys()):
            content = files[path]
            parts.append(f"### FILE: {path}")
            parts.append(f"### LINES: {len(content.splitlines())}")
            parts.append("-" * 40)
            
            # Add line numbers for searchability
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                parts.append(f"{i:5d} | {line}")
            
            parts.append("")
            parts.append("### END FILE: " + path)
            parts.append("")
        
        return "\n".join(parts)
    
    def get_file_list(self) -> List[Dict[str, Any]]:
        """Get list of indexed files with metadata."""
        files = self._collect_files()
        result = []
        
        for path, content in sorted(files.items()):
            result.append({
                "path": path,
                "lines": len(content.splitlines()),
                "chars": len(content),
                "hash": hashlib.sha256(content.encode()).hexdigest()[:8]
            })
            
        return result


# =============================================================================
# ALEPH CONTEXT MANAGER
# =============================================================================

class AlephContextManager:
    """
    Manages Aleph context for a project.
    Handles loading, searching, and evidence tracking.
    """
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.indexer = CodebaseIndexer(project_dir)
        self._context_id = "codebase"
        self._context_loaded = False
        self._evidence: List[Dict[str, Any]] = []
        
        # Planning files context (separate, always small)
        self._planning_context_id = "planning"
        
    def index_codebase(self, force: bool = False) -> Dict[str, Any]:
        """
        Index the codebase into Aleph.
        Returns stats about the indexing operation.
        """
        if not ALEPH_AVAILABLE:
            return {
                "success": False,
                "error": "Aleph not installed. Run: pip install aleph-rlm[mcp]"
            }
        
        needs_index = force or self.indexer.needs_reindex()
        
        if not needs_index and self._context_loaded:
            return {
                "success": True,
                "action": "skipped",
                "reason": "Codebase unchanged since last index"
            }
        
        # Build and load context
        context_str = self.indexer.build_context()
        
        # Use Aleph's load_context
        # This stores the content outside the LLM's context window
        try:
            from aleph import load_context
            load_context(context=context_str, context_id=self._context_id)
            self._context_loaded = True
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load context into Aleph: {e}"
            }
        
        return {
            "success": True,
            "action": "indexed",
            "files": len(self.indexer._indexed_files),
            "total_chars": self.indexer._last_index_size,
            "context_id": self._context_id
        }
    
    def search_codebase(
        self, 
        pattern: str, 
        context_lines: int = 3,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Search the indexed codebase using regex pattern.
        Returns matches with surrounding context.
        """
        if not ALEPH_AVAILABLE:
            return {"error": "Aleph not installed"}
            
        if not self._context_loaded:
            # Auto-index if not done
            index_result = self.index_codebase()
            if not index_result.get("success"):
                return index_result
        
        try:
            from aleph import search_context
            results = search_context(
                pattern=pattern,
                context_id=self._context_id,
                context_lines=context_lines,
                max_results=max_results
            )
            return {
                "success": True,
                "pattern": pattern,
                "matches": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def peek_file(
        self, 
        file_path: str, 
        start_line: int = 1, 
        end_line: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        View specific lines of a file without loading entire codebase.
        """
        full_path = self.project_dir / file_path
        
        if not full_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            
            # Adjust indices
            start_idx = max(0, start_line - 1)
            end_idx = end_line if end_line else len(lines)
            
            selected = lines[start_idx:end_idx]
            
            return {
                "success": True,
                "file": file_path,
                "start_line": start_line,
                "end_line": end_idx,
                "total_lines": len(lines),
                "content": "\n".join(f"{i+start_line:5d} | {line}" 
                                     for i, line in enumerate(selected))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cite_finding(
        self, 
        file_path: str, 
        line_start: int, 
        line_end: int, 
        note: str
    ) -> Dict[str, Any]:
        """
        Record a citation/evidence trail for a finding.
        """
        citation = {
            "file": file_path,
            "lines": f"{line_start}-{line_end}",
            "note": note,
            "timestamp": datetime.now().isoformat()
        }
        self._evidence.append(citation)
        
        return {
            "success": True,
            "citation_id": len(self._evidence),
            "citation": citation
        }
    
    def get_evidence(self) -> List[Dict[str, Any]]:
        """Get all collected evidence/citations."""
        return self._evidence
    
    def load_planning_files(self) -> Dict[str, Any]:
        """
        Load planning files (task_plan.md, findings.md, progress.md) into Aleph.
        These are kept separate from codebase for targeted queries.
        """
        planning_files = ["task_plan.md", "findings.md", "progress.md"]
        contents = []
        
        for filename in planning_files:
            file_path = self.project_dir / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8", errors="replace")
                contents.append(f"### {filename}\n{content}\n")
        
        if not contents:
            return {
                "success": False, 
                "error": "No planning files found. Run init-session.sh first."
            }
        
        combined = "\n".join(contents)
        
        if ALEPH_AVAILABLE:
            try:
                from aleph import load_context
                load_context(context=combined, context_id=self._planning_context_id)
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "files_loaded": len(contents),
            "total_chars": len(combined),
            "context_id": self._planning_context_id
        }


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

# Global manager instance (initialized per project)
_manager: Optional[AlephContextManager] = None


def init_aleph_bridge(project_dir: str) -> Dict[str, Any]:
    """
    Initialize the Aleph bridge for a project.
    Call this at the start of each autocoder session.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        Status dict with initialization results
    """
    global _manager
    _manager = AlephContextManager(Path(project_dir))
    
    # Initial indexing
    index_result = _manager.index_codebase()
    planning_result = _manager.load_planning_files()
    
    return {
        "success": True,
        "project_dir": project_dir,
        "codebase_index": index_result,
        "planning_files": planning_result,
        "aleph_available": ALEPH_AVAILABLE
    }


def refresh_codebase_index(force: bool = False) -> Dict[str, Any]:
    """
    Refresh the codebase index after making changes.
    Call this after completing a feature or making significant edits.
    
    Args:
        force: Force re-index even if no changes detected
        
    Returns:
        Status dict with indexing results
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    return _manager.index_codebase(force=force)


def search_codebase(
    pattern: str, 
    context_lines: int = 3,
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Search the codebase for a regex pattern.
    Use this instead of grep/cat for large codebases.
    
    Args:
        pattern: Regex pattern to search for
        context_lines: Number of surrounding lines to include
        max_results: Maximum matches to return
        
    Returns:
        Dict with matches and their locations
        
    Examples:
        search_codebase("def.*auth")  # Find auth-related functions
        search_codebase("import.*from")  # Find imports
        search_codebase("TODO|FIXME")  # Find todos
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    return _manager.search_codebase(pattern, context_lines, max_results)


def peek_file(
    file_path: str, 
    start_line: int = 1, 
    end_line: Optional[int] = None
) -> Dict[str, Any]:
    """
    View specific lines of a file without loading the entire codebase.
    More efficient than cat for targeted inspection.
    
    Args:
        file_path: Relative path to file from project root
        start_line: First line to show (1-indexed)
        end_line: Last line to show (optional, shows to end if omitted)
        
    Returns:
        Dict with file content and metadata
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    return _manager.peek_file(file_path, start_line, end_line)


def list_indexed_files() -> Dict[str, Any]:
    """
    List all files currently indexed in Aleph.
    
    Returns:
        Dict with list of files and their metadata
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    return {
        "success": True,
        "files": _manager.indexer.get_file_list()
    }


def cite_code(
    file_path: str, 
    line_start: int, 
    line_end: int, 
    note: str
) -> Dict[str, Any]:
    """
    Record a citation for code you're referencing or modifying.
    Builds an evidence trail for decisions.
    
    Args:
        file_path: Path to the file
        line_start: Starting line of the citation
        line_end: Ending line of the citation
        note: Description of why this code is relevant
        
    Returns:
        Dict with citation details
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    return _manager.cite_finding(file_path, line_start, line_end, note)


def get_evidence_trail() -> Dict[str, Any]:
    """
    Get all citations/evidence collected during this session.
    Useful for documenting decisions in progress.md.
    
    Returns:
        Dict with list of all citations
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    return {
        "success": True,
        "evidence": _manager.get_evidence()
    }


def search_planning_files(pattern: str) -> Dict[str, Any]:
    """
    Search the planning files (task_plan.md, findings.md, progress.md).
    Use this to recall decisions, findings, or progress notes.
    
    Args:
        pattern: Regex pattern to search for
        
    Returns:
        Dict with matches from planning files
    """
    if _manager is None:
        return {"success": False, "error": "Aleph bridge not initialized"}
    
    if not ALEPH_AVAILABLE:
        return {"success": False, "error": "Aleph not installed"}
    
    try:
        from aleph import search_context
        results = search_context(
            pattern=pattern,
            context_id=_manager._planning_context_id,
            context_lines=5
        )
        return {
            "success": True,
            "pattern": pattern,
            "matches": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MCP SERVER REGISTRATION
# =============================================================================

def get_aleph_tools() -> List[Dict[str, Any]]:
    """
    Get tool definitions for MCP server registration.
    These follow the MCP tool schema format.
    """
    return [
        {
            "name": "aleph_init",
            "description": "Initialize Aleph bridge for the project. Call at session start.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to the project directory"
                    }
                },
                "required": ["project_dir"]
            }
        },
        {
            "name": "aleph_refresh",
            "description": "Refresh codebase index. Call after completing features.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force re-index even if unchanged",
                        "default": False
                    }
                }
            }
        },
        {
            "name": "aleph_search",
            "description": "Search codebase with regex. Use instead of grep for large codebases.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Surrounding lines to include",
                        "default": 3
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum matches to return",
                        "default": 20
                    }
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "aleph_peek",
            "description": "View specific lines of a file efficiently.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to file"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "First line (1-indexed)",
                        "default": 1
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Last line (optional)"
                    }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "aleph_list_files",
            "description": "List all indexed files with metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "aleph_cite",
            "description": "Record a citation for code being referenced or modified.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "line_start": {
                        "type": "integer",
                        "description": "Starting line"
                    },
                    "line_end": {
                        "type": "integer",
                        "description": "Ending line"
                    },
                    "note": {
                        "type": "string",
                        "description": "Why this code is relevant"
                    }
                },
                "required": ["file_path", "line_start", "line_end", "note"]
            }
        },
        {
            "name": "aleph_evidence",
            "description": "Get all citations collected during this session.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "aleph_search_planning",
            "description": "Search planning files (task_plan.md, findings.md, progress.md).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    }
                },
                "required": ["pattern"]
            }
        }
    ]


def handle_aleph_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle an Aleph tool call from MCP.
    
    Args:
        name: Tool name (aleph_*)
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    handlers = {
        "aleph_init": lambda args: init_aleph_bridge(args["project_dir"]),
        "aleph_refresh": lambda args: refresh_codebase_index(args.get("force", False)),
        "aleph_search": lambda args: search_codebase(
            args["pattern"], 
            args.get("context_lines", 3),
            args.get("max_results", 20)
        ),
        "aleph_peek": lambda args: peek_file(
            args["file_path"],
            args.get("start_line", 1),
            args.get("end_line")
        ),
        "aleph_list_files": lambda args: list_indexed_files(),
        "aleph_cite": lambda args: cite_code(
            args["file_path"],
            args["line_start"],
            args["line_end"],
            args["note"]
        ),
        "aleph_evidence": lambda args: get_evidence_trail(),
        "aleph_search_planning": lambda args: search_planning_files(args["pattern"])
    }
    
    handler = handlers.get(name)
    if handler is None:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    try:
        return handler(arguments)
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# INTEGRATION HOOKS FOR AUTOCODER
# =============================================================================

def on_feature_complete(project_dir: str, feature_id: int) -> Dict[str, Any]:
    """
    Hook called when autocoder marks a feature as complete.
    Refreshes the Aleph index to include new code.
    
    Args:
        project_dir: Project directory path
        feature_id: ID of the completed feature
        
    Returns:
        Status dict
    """
    global _manager
    
    # Ensure manager is initialized
    if _manager is None:
        init_aleph_bridge(project_dir)
    
    # Refresh index
    result = refresh_codebase_index(force=True)
    result["trigger"] = f"feature_{feature_id}_complete"
    
    return result


def on_session_start(project_dir: str) -> Dict[str, Any]:
    """
    Hook called at the start of an autocoder session.
    Initializes Aleph and loads existing codebase.
    
    Args:
        project_dir: Project directory path
        
    Returns:
        Status dict with initialization results
    """
    return init_aleph_bridge(project_dir)


def on_session_end(project_dir: str) -> Dict[str, Any]:
    """
    Hook called at the end of an autocoder session.
    Saves evidence trail to progress.md.
    
    Args:
        project_dir: Project directory path
        
    Returns:
        Status dict
    """
    if _manager is None:
        return {"success": False, "error": "No active session"}
    
    evidence = _manager.get_evidence()
    
    if evidence:
        # Append evidence to progress.md
        progress_file = Path(project_dir) / "progress.md"
        
        if progress_file.exists():
            content = progress_file.read_text()
        else:
            content = "# Progress Log\n\n"
        
        # Add evidence section
        content += f"\n## Evidence Trail - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for i, e in enumerate(evidence, 1):
            content += f"{i}. **{e['file']}** (lines {e['lines']})\n"
            content += f"   - {e['note']}\n"
        
        progress_file.write_text(content)
        
        return {
            "success": True,
            "evidence_saved": len(evidence),
            "file": str(progress_file)
        }
    
    return {"success": True, "evidence_saved": 0}


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python aleph_bridge.py <project_dir> [command]")
        print("Commands: init, search <pattern>, peek <file> [start] [end], list")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "init"
    
    if command == "init":
        result = init_aleph_bridge(project_dir)
        print(json.dumps(result, indent=2))
        
    elif command == "search" and len(sys.argv) > 3:
        init_aleph_bridge(project_dir)
        result = search_codebase(sys.argv[3])
        print(json.dumps(result, indent=2))
        
    elif command == "peek" and len(sys.argv) > 3:
        init_aleph_bridge(project_dir)
        start = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        end = int(sys.argv[5]) if len(sys.argv) > 5 else None
        result = peek_file(sys.argv[3], start, end)
        print(json.dumps(result, indent=2))
        
    elif command == "list":
        init_aleph_bridge(project_dir)
        result = list_indexed_files()
        print(json.dumps(result, indent=2))
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
