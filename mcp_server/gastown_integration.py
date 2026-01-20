"""
Gastown Integration for Vibecoding Stack
=========================================

Git-backed persistent state management inspired by Gastown's architecture.

Key concepts:
- Bead: A git-backed work unit (replaces SQLite Feature rows)
- Convoy: A group of related Beads assigned to an agent
- Mayor: High-level orchestrator that coordinates Convoys
- Hooks: Git worktree-based persistence (survives crashes)

Benefits over SQLite:
- Crash-proof: State lives in git, survives any failure
- Auditable: Full history of every state change
- Distributed: Can sync across machines via git
- Mergeable: Multiple agents can work without conflicts
"""

import os
import json
import subprocess
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum


# =============================================================================
# BEAD STATUS
# =============================================================================

class BeadStatus(str, Enum):
    """Status values for Beads (mirrors Feature status)."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSING = "passing"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"


class QualityStatus(str, Enum):
    """Quality gate status for Beads."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


# =============================================================================
# BEAD (Git-backed Work Unit)
# =============================================================================

@dataclass
class QualityState:
    """Quality gate state for a Bead."""
    status: str = "pending"
    tests: str = "pending"
    lint: str = "pending"
    types: str = "pending"
    format: str = "pending"
    security: str = "pending"
    build: str = "pending"
    last_run: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Bead:
    """
    A git-backed work unit.

    Replaces SQLite Feature rows with YAML files stored in .git/beads/.
    Each state change is a git commit, providing full audit trail.
    """
    id: str  # e.g., "gt-feat-001"
    name: str
    description: str = ""
    test_cases: List[str] = field(default_factory=list)
    status: str = "pending"
    priority: int = 0
    verification_status: str = "pending"
    verification_notes: str = ""
    quality_state: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Convoy association
    convoy_id: Optional[str] = None

    # Metadata
    assigned_to: Optional[str] = None  # Polecat ID
    git_commit: Optional[str] = None   # Last commit that modified this bead

    def to_yaml(self) -> str:
        """Serialize Bead to YAML."""
        # Convert status to string if it's an enum
        status = self.status.value if isinstance(self.status, BeadStatus) else self.status
        verification_status = self.verification_status

        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_cases": self.test_cases,
            "status": status,
            "priority": self.priority,
            "verification_status": verification_status,
            "verification_notes": self.verification_notes,
            "quality_state": self.quality_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "convoy_id": self.convoy_id,
            "assigned_to": self.assigned_to,
            "git_commit": self.git_commit,
        }
        # Remove None values for cleaner YAML
        data = {k: v for k, v in data.items() if v is not None}
        return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Bead":
        """Deserialize Bead from YAML."""
        data = yaml.safe_load(yaml_content)
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            test_cases=data.get("test_cases", []),
            status=data.get("status", "pending"),
            priority=data.get("priority", 0),
            verification_status=data.get("verification_status", "pending"),
            verification_notes=data.get("verification_notes", ""),
            quality_state=data.get("quality_state"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            convoy_id=data.get("convoy_id"),
            assigned_to=data.get("assigned_to"),
            git_commit=data.get("git_commit"),
        )

    def to_feature_dict(self) -> Dict[str, Any]:
        """Convert to Feature-compatible dict for backward compatibility."""
        # Convert status to string if it's an enum
        status = self.status.value if isinstance(self.status, BeadStatus) else self.status

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_cases": self.test_cases,
            "status": status,
            "priority": self.priority,
            "verification_status": self.verification_status,
            "verification_notes": self.verification_notes,
        }


# =============================================================================
# BEAD STORE (Git-backed Storage)
# =============================================================================

class BeadStore:
    """
    Git-backed storage for Beads.

    Stores Beads as YAML files in .git/beads/ directory.
    Each save commits to git for full audit trail.
    """

    def __init__(self, project_dir: Path, auto_commit: bool = True):
        self.project_dir = Path(project_dir)
        self.beads_dir = self.project_dir / ".git" / "beads"
        self.auto_commit = auto_commit
        self._ensure_beads_dir()

    def _ensure_beads_dir(self) -> None:
        """Create beads directory if it doesn't exist."""
        self.beads_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitkeep to ensure directory is tracked
        gitkeep = self.beads_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    def _bead_path(self, bead_id: str) -> Path:
        """Get path to a bead file."""
        return self.beads_dir / f"{bead_id}.yaml"

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the project directory."""
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            check=check
        )

    def _get_current_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = self._run_git("rev-parse", "HEAD", check=False)
            if result.returncode == 0:
                return result.stdout.strip()[:12]
        except Exception:
            pass
        return None

    def save(self, bead: Bead, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Save a Bead to git.

        Args:
            bead: The Bead to save
            message: Optional commit message

        Returns:
            Result dict with success status and commit info
        """
        bead.updated_at = datetime.now().isoformat()

        # Write YAML file
        bead_path = self._bead_path(bead.id)
        bead_path.write_text(bead.to_yaml())

        if self.auto_commit:
            # Stage and commit
            rel_path = bead_path.relative_to(self.project_dir)
            self._run_git("add", str(rel_path), check=False)

            commit_msg = message or f"Update bead: {bead.id} ({bead.status})"
            result = self._run_git("commit", "-m", commit_msg, "--allow-empty", check=False)

            # Update bead with commit hash
            bead.git_commit = self._get_current_commit()

        return {
            "success": True,
            "bead_id": bead.id,
            "path": str(bead_path),
            "git_commit": bead.git_commit
        }

    def load(self, bead_id: str) -> Optional[Bead]:
        """Load a Bead from git."""
        bead_path = self._bead_path(bead_id)

        if not bead_path.exists():
            return None

        yaml_content = bead_path.read_text()
        return Bead.from_yaml(yaml_content)

    def load_all(self) -> List[Bead]:
        """Load all Beads from git."""
        beads = []

        for bead_file in self.beads_dir.glob("*.yaml"):
            if bead_file.name == ".gitkeep":
                continue
            try:
                yaml_content = bead_file.read_text()
                bead = Bead.from_yaml(yaml_content)
                beads.append(bead)
            except Exception as e:
                print(f"Warning: Could not load bead from {bead_file}: {e}")

        return beads

    def delete(self, bead_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """Delete a Bead from git."""
        bead_path = self._bead_path(bead_id)

        if not bead_path.exists():
            return {"success": False, "error": f"Bead {bead_id} not found"}

        bead_path.unlink()

        if self.auto_commit:
            rel_path = bead_path.relative_to(self.project_dir)
            self._run_git("add", str(rel_path), check=False)

            commit_msg = message or f"Delete bead: {bead_id}"
            self._run_git("commit", "-m", commit_msg, "--allow-empty", check=False)

        return {"success": True, "bead_id": bead_id}

    def get_next(self) -> Optional[Bead]:
        """
        Get the next Bead to work on.

        Priority:
        1. In-progress beads (resume work)
        2. Needs-review beads (fix issues)
        3. Pending beads by priority
        """
        beads = self.load_all()

        # First: in-progress
        in_progress = [b for b in beads if b.status == BeadStatus.IN_PROGRESS]
        if in_progress:
            return in_progress[0]

        # Second: needs review
        needs_review = [b for b in beads if b.status == BeadStatus.NEEDS_REVIEW]
        if needs_review:
            return needs_review[0]

        # Third: pending by priority
        pending = [b for b in beads if b.status == BeadStatus.PENDING]
        if pending:
            pending.sort(key=lambda b: (-b.priority, b.id))
            return pending[0]

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about Beads."""
        beads = self.load_all()

        total = len(beads)
        by_status = {}
        for status in BeadStatus:
            by_status[status.value] = len([b for b in beads if b.status == status.value])

        passing = by_status.get("passing", 0)
        progress_percent = round((passing / total * 100) if total > 0 else 0, 1)

        return {
            "total": total,
            "passing": passing,
            "pending": by_status.get("pending", 0),
            "in_progress": by_status.get("in_progress", 0),
            "skipped": by_status.get("skipped", 0),
            "needs_review": by_status.get("needs_review", 0),
            "progress_percent": progress_percent
        }

    def generate_id(self, prefix: str = "gt-feat") -> str:
        """Generate a unique Bead ID."""
        existing = {b.id for b in self.load_all()}

        # Find next available number
        for i in range(1, 10000):
            candidate = f"{prefix}-{i:03d}"
            if candidate not in existing:
                return candidate

        # Fallback to hash-based ID
        timestamp = datetime.now().isoformat()
        hash_suffix = hashlib.sha256(timestamp.encode()).hexdigest()[:6]
        return f"{prefix}-{hash_suffix}"


# =============================================================================
# CONVOY (Group of Related Beads)
# =============================================================================

@dataclass
class Convoy:
    """
    A group of related Beads assigned to an agent.

    Convoys allow:
    - Grouping related work ("Auth feature = login + token + session")
    - Tracking progress across multiple Beads
    - Assigning work to a Polecat
    """
    id: str
    name: str
    bead_ids: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, complete
    assigned_to: Optional[str] = None  # Polecat ID
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_yaml(self) -> str:
        """Serialize Convoy to YAML."""
        data = asdict(self)
        data = {k: v for k, v in data.items() if v is not None}
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Convoy":
        """Deserialize Convoy from YAML."""
        data = yaml.safe_load(yaml_content)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConvoyStore:
    """Git-backed storage for Convoys."""

    def __init__(self, project_dir: Path, auto_commit: bool = True):
        self.project_dir = Path(project_dir)
        self.convoys_dir = self.project_dir / ".git" / "convoys"
        self.auto_commit = auto_commit
        self._ensure_convoys_dir()

    def _ensure_convoys_dir(self) -> None:
        """Create convoys directory if it doesn't exist."""
        self.convoys_dir.mkdir(parents=True, exist_ok=True)

    def _convoy_path(self, convoy_id: str) -> Path:
        """Get path to a convoy file."""
        return self.convoys_dir / f"{convoy_id}.yaml"

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the project directory."""
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            check=check
        )

    def save(self, convoy: Convoy, message: Optional[str] = None) -> Dict[str, Any]:
        """Save a Convoy to git."""
        convoy.updated_at = datetime.now().isoformat()

        convoy_path = self._convoy_path(convoy.id)
        convoy_path.write_text(convoy.to_yaml())

        if self.auto_commit:
            rel_path = convoy_path.relative_to(self.project_dir)
            self._run_git("add", str(rel_path), check=False)

            commit_msg = message or f"Update convoy: {convoy.id} ({convoy.status})"
            self._run_git("commit", "-m", commit_msg, "--allow-empty", check=False)

        return {"success": True, "convoy_id": convoy.id}

    def load(self, convoy_id: str) -> Optional[Convoy]:
        """Load a Convoy from git."""
        convoy_path = self._convoy_path(convoy_id)

        if not convoy_path.exists():
            return None

        yaml_content = convoy_path.read_text()
        return Convoy.from_yaml(yaml_content)

    def load_all(self) -> List[Convoy]:
        """Load all Convoys from git."""
        convoys = []

        for convoy_file in self.convoys_dir.glob("*.yaml"):
            try:
                yaml_content = convoy_file.read_text()
                convoy = Convoy.from_yaml(yaml_content)
                convoys.append(convoy)
            except Exception as e:
                print(f"Warning: Could not load convoy from {convoy_file}: {e}")

        return convoys

    def generate_id(self) -> str:
        """Generate a unique Convoy ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_suffix = hashlib.sha256(timestamp.encode()).hexdigest()[:4]
        return f"convoy-{timestamp}-{hash_suffix}"


# =============================================================================
# MAYOR (Orchestrator)
# =============================================================================

class Mayor:
    """
    High-level orchestrator for Beads and Convoys.

    The Mayor:
    - Creates and manages Convoys
    - Assigns work to Polecats (agents)
    - Tracks overall progress
    - Handles crash recovery
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.bead_store = BeadStore(project_dir)
        self.convoy_store = ConvoyStore(project_dir)

    def create_bead(
        self,
        name: str,
        description: str = "",
        test_cases: List[str] = None,
        priority: int = 0
    ) -> Bead:
        """Create a new Bead."""
        bead_id = self.bead_store.generate_id()

        bead = Bead(
            id=bead_id,
            name=name,
            description=description,
            test_cases=test_cases or [],
            priority=priority,
            status=BeadStatus.PENDING
        )

        self.bead_store.save(bead, f"Create bead: {name}")
        return bead

    def create_beads_bulk(self, features: List[Dict[str, Any]]) -> List[Bead]:
        """Create multiple Beads at once."""
        beads = []

        for i, f in enumerate(features):
            bead = self.create_bead(
                name=f.get("name", f"Feature {i+1}"),
                description=f.get("description", ""),
                test_cases=f.get("test_cases", []),
                priority=f.get("priority", len(features) - i)
            )
            beads.append(bead)

        return beads

    def get_next_bead(self) -> Optional[Bead]:
        """Get the next Bead to work on."""
        bead = self.bead_store.get_next()

        if bead and bead.status == BeadStatus.PENDING:
            # Mark as in-progress
            bead.status = BeadStatus.IN_PROGRESS
            self.bead_store.save(bead, f"Start working on: {bead.name}")

        return bead

    def mark_bead_passing(
        self,
        bead_id: str,
        quality_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mark a Bead as passing."""
        bead = self.bead_store.load(bead_id)

        if not bead:
            return {"error": f"Bead {bead_id} not found"}

        # Check quality result
        if quality_result and quality_result.get("status") == "failed":
            bead.status = BeadStatus.NEEDS_REVIEW
            bead.verification_status = "failed"
            bead.verification_notes = json.dumps(quality_result)
            self.bead_store.save(bead, f"Quality check failed: {bead.name}")

            return {
                "success": False,
                "bead_id": bead_id,
                "name": bead.name,
                "new_status": BeadStatus.NEEDS_REVIEW,
                "quality_result": quality_result,
                "message": "Quality checks failed. Fix issues before marking complete."
            }

        # Mark as passing
        bead.status = BeadStatus.PASSING
        bead.verification_status = "verified"
        if quality_result:
            bead.quality_state = quality_result

        self.bead_store.save(bead, f"Complete: {bead.name}")

        return {
            "success": True,
            "bead_id": bead_id,
            "name": bead.name,
            "new_status": BeadStatus.PASSING,
            "progress": self.bead_store.get_stats()
        }

    def skip_bead(self, bead_id: str, reason: str = "") -> Dict[str, Any]:
        """Skip a Bead (move to end of queue)."""
        bead = self.bead_store.load(bead_id)

        if not bead:
            return {"error": f"Bead {bead_id} not found"}

        bead.status = BeadStatus.PENDING
        bead.priority = bead.priority - 100

        self.bead_store.save(bead, f"Skip: {bead.name} - {reason}")

        return {
            "success": True,
            "bead_id": bead_id,
            "name": bead.name,
            "reason": reason,
            "new_priority": bead.priority
        }

    def create_convoy(self, name: str, bead_ids: List[str]) -> Convoy:
        """Create a Convoy grouping related Beads."""
        convoy_id = self.convoy_store.generate_id()

        convoy = Convoy(
            id=convoy_id,
            name=name,
            bead_ids=bead_ids,
            status="pending"
        )

        # Update beads with convoy reference
        for bead_id in bead_ids:
            bead = self.bead_store.load(bead_id)
            if bead:
                bead.convoy_id = convoy_id
                self.bead_store.save(bead)

        self.convoy_store.save(convoy, f"Create convoy: {name}")
        return convoy

    def get_convoy_status(self, convoy_id: str) -> Dict[str, Any]:
        """Get status of a Convoy and its Beads."""
        convoy = self.convoy_store.load(convoy_id)

        if not convoy:
            return {"error": f"Convoy {convoy_id} not found"}

        beads = []
        for bead_id in convoy.bead_ids:
            bead = self.bead_store.load(bead_id)
            if bead:
                beads.append(bead.to_feature_dict())

        complete = sum(1 for b in beads if b["status"] == "passing")
        total = len(beads)

        return {
            "convoy_id": convoy_id,
            "name": convoy.name,
            "status": convoy.status,
            "progress": f"{complete}/{total}",
            "beads": beads
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        return self.bead_store.get_stats()


# =============================================================================
# MIGRATION UTILITIES
# =============================================================================

def migrate_feature_to_bead(feature_dict: Dict[str, Any], bead_store: BeadStore) -> Bead:
    """
    Migrate a SQLite Feature to a git-backed Bead.

    Args:
        feature_dict: Feature data from SQLite
        bead_store: BeadStore to save to

    Returns:
        Created Bead
    """
    # Generate ID from original feature ID if numeric
    original_id = feature_dict.get("id")
    if isinstance(original_id, int):
        bead_id = f"gt-feat-{original_id:03d}"
    else:
        bead_id = bead_store.generate_id()

    # Handle test_cases (may be JSON string or list)
    test_cases = feature_dict.get("test_cases", [])
    if isinstance(test_cases, str):
        try:
            test_cases = json.loads(test_cases)
        except json.JSONDecodeError:
            test_cases = []

    bead = Bead(
        id=bead_id,
        name=feature_dict.get("name", ""),
        description=feature_dict.get("description", ""),
        test_cases=test_cases,
        status=feature_dict.get("status", "pending"),
        priority=feature_dict.get("priority", 0),
        verification_status=feature_dict.get("verification_status", "pending"),
        verification_notes=feature_dict.get("verification_notes", ""),
        created_at=feature_dict.get("created_at", datetime.now().isoformat()),
        updated_at=feature_dict.get("updated_at", datetime.now().isoformat()),
    )

    bead_store.save(bead, f"Migrate from SQLite: {bead.name}")
    return bead


# =============================================================================
# FEATURE-COMPATIBLE WRAPPER
# =============================================================================

class BeadFeatureAdapter:
    """
    Adapter that makes BeadStore behave like the old SQLite feature system.

    This allows gradual migration without breaking existing code.
    """

    def __init__(self, project_dir: Path):
        self.mayor = Mayor(project_dir)
        self.bead_store = self.mayor.bead_store

    def get_stats(self) -> Dict[str, Any]:
        """Get feature statistics (compatible with feature_get_stats)."""
        return self.bead_store.get_stats()

    def get_next(self) -> Dict[str, Any]:
        """Get next feature (compatible with feature_get_next)."""
        bead = self.mayor.get_next_bead()

        if bead is None:
            return {"message": "All features complete!", "remaining": 0}

        result = bead.to_feature_dict()

        if bead.status == BeadStatus.IN_PROGRESS:
            result["note"] = "Resuming in-progress feature"
        elif bead.status == BeadStatus.NEEDS_REVIEW:
            result["note"] = "Feature needs review before marking complete"

        return result

    def mark_passing(
        self,
        feature_id: str,
        skip_verification: bool = False,
        quality_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mark feature as passing (compatible with feature_mark_passing)."""
        # Convert int ID to bead ID if needed
        if isinstance(feature_id, int):
            feature_id = f"gt-feat-{feature_id:03d}"

        return self.mayor.mark_bead_passing(feature_id, quality_result)

    def skip(self, feature_id: str, reason: str = "") -> Dict[str, Any]:
        """Skip feature (compatible with feature_skip)."""
        if isinstance(feature_id, int):
            feature_id = f"gt-feat-{feature_id:03d}"

        return self.mayor.skip_bead(feature_id, reason)

    def create_bulk(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple features (compatible with feature_create_bulk)."""
        beads = self.mayor.create_beads_bulk(features)

        return {
            "success": True,
            "created_count": len(beads),
            "features": [b.name for b in beads]
        }

    def get_for_regression(self, count: int = 3) -> Dict[str, Any]:
        """Get random passing features for regression testing."""
        import random

        beads = self.bead_store.load_all()
        passing = [b for b in beads if b.status == BeadStatus.PASSING]

        if not passing:
            return {"features": [], "message": "No passing features yet"}

        selected = random.sample(passing, min(count, len(passing)))

        return {
            "features": [b.to_feature_dict() for b in selected]
        }

    def verify(self, feature_id: str) -> Dict[str, Any]:
        """Get feature for verification."""
        if isinstance(feature_id, int):
            feature_id = f"gt-feat-{feature_id:03d}"

        bead = self.bead_store.load(feature_id)

        if not bead:
            return {"error": f"Feature {feature_id} not found"}

        return bead.to_feature_dict()


# =============================================================================
# MCP TOOL DEFINITIONS (Kanban-style)
# =============================================================================

def get_kanban_tools() -> List[Dict[str, Any]]:
    """Get kanban-style tool definitions for MCP."""
    return [
        {
            "name": "kanban_get_board",
            "description": "Get the kanban board state with all columns (To Do, In Progress, Review, Done).",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "kanban_move_task",
            "description": "Move a task to a different column.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "bead_id": {
                        "type": "string",
                        "description": "ID of the bead/task to move"
                    },
                    "column": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "review", "done"],
                        "description": "Target column"
                    }
                },
                "required": ["bead_id", "column"]
            }
        },
        {
            "name": "kanban_create_task",
            "description": "Create a new task on the board.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Task name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "test_cases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Test cases for the task"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (higher = more important)"
                    }
                },
                "required": ["name"]
            }
        }
    ]


# Global instance for MCP
_kanban_adapter: Optional[BeadFeatureAdapter] = None


def init_kanban_system(project_dir: str) -> Dict[str, Any]:
    """Initialize the kanban/bead system."""
    global _kanban_adapter

    _kanban_adapter = BeadFeatureAdapter(Path(project_dir))

    return {
        "success": True,
        "project_dir": project_dir,
        "beads_dir": str(_kanban_adapter.bead_store.beads_dir),
        "backend": "gastown_beads"
    }


def handle_kanban_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a kanban tool call."""
    if _kanban_adapter is None:
        return {"error": "Kanban system not initialized"}

    if name == "kanban_get_board":
        beads = _kanban_adapter.bead_store.load_all()

        # Group by status
        board = {
            "todo": [b.to_feature_dict() for b in beads if b.status == BeadStatus.PENDING],
            "in_progress": [b.to_feature_dict() for b in beads if b.status == BeadStatus.IN_PROGRESS],
            "review": [b.to_feature_dict() for b in beads if b.status == BeadStatus.NEEDS_REVIEW],
            "done": [b.to_feature_dict() for b in beads if b.status == BeadStatus.PASSING],
        }

        return {
            "board": board,
            "stats": _kanban_adapter.get_stats()
        }

    elif name == "kanban_move_task":
        bead_id = arguments["bead_id"]
        column = arguments["column"]

        # Map column to status
        column_to_status = {
            "todo": BeadStatus.PENDING,
            "in_progress": BeadStatus.IN_PROGRESS,
            "review": BeadStatus.NEEDS_REVIEW,
            "done": BeadStatus.PASSING
        }

        bead = _kanban_adapter.bead_store.load(bead_id)
        if not bead:
            return {"error": f"Bead {bead_id} not found"}

        old_status = bead.status
        bead.status = column_to_status[column]
        _kanban_adapter.bead_store.save(bead, f"Move {bead.name}: {old_status} -> {column}")

        return {
            "success": True,
            "bead_id": bead_id,
            "old_status": old_status,
            "new_status": bead.status
        }

    elif name == "kanban_create_task":
        bead = _kanban_adapter.mayor.create_bead(
            name=arguments["name"],
            description=arguments.get("description", ""),
            test_cases=arguments.get("test_cases", []),
            priority=arguments.get("priority", 0)
        )

        return {
            "success": True,
            "bead_id": bead.id,
            "name": bead.name
        }

    return {"error": f"Unknown kanban tool: {name}"}


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    # Test with current directory
    project_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    print("=== GASTOWN INTEGRATION TEST ===")
    print(f"Project: {project_dir}")

    # Initialize
    mayor = Mayor(project_dir)

    # Create test beads
    print("\n--- Creating test beads ---")
    bead1 = mayor.create_bead(
        name="User Authentication",
        description="Implement JWT-based auth",
        test_cases=["Login works", "Logout works", "Token refresh works"],
        priority=100
    )
    print(f"Created: {bead1.id} - {bead1.name}")

    bead2 = mayor.create_bead(
        name="User Profile",
        description="Profile page with editing",
        test_cases=["View profile", "Edit profile"],
        priority=50
    )
    print(f"Created: {bead2.id} - {bead2.name}")

    # Get stats
    print("\n--- Stats ---")
    print(json.dumps(mayor.get_stats(), indent=2))

    # Get next
    print("\n--- Get Next ---")
    next_bead = mayor.get_next_bead()
    if next_bead:
        print(f"Next: {next_bead.id} - {next_bead.name} ({next_bead.status})")

    # Mark passing
    print("\n--- Mark Passing ---")
    result = mayor.mark_bead_passing(bead1.id)
    print(json.dumps(result, indent=2))

    # Final stats
    print("\n--- Final Stats ---")
    print(json.dumps(mayor.get_stats(), indent=2))
