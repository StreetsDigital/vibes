"""
Task Progress Tracker
======================

Tracks Claude's progress on tasks with stage updates and auto-retros.

Stages:
1. STARTING - Task picked up
2. ANALYZING - Understanding the problem
3. PLANNING - Designing the solution
4. IMPLEMENTING - Writing code
5. TESTING - Running tests
6. REVIEWING - Self-review
7. COMPLETED - Done with 2-sentence retro
"""

import json
import threading
import time
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Callable, Dict, Any
from pathlib import Path


class TaskStage(Enum):
    """Stages of task execution."""
    STARTING = "starting"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def emoji(self) -> str:
        return {
            "starting": "🚀",
            "analyzing": "🔍",
            "planning": "📝",
            "implementing": "💻",
            "testing": "🧪",
            "reviewing": "👀",
            "completed": "✅",
            "failed": "❌"
        }.get(self.value, "📌")

    @property
    def display_name(self) -> str:
        return {
            "starting": "Starting",
            "analyzing": "Analyzing",
            "planning": "Planning",
            "implementing": "Implementing",
            "testing": "Testing",
            "reviewing": "Reviewing",
            "completed": "Completed",
            "failed": "Failed"
        }.get(self.value, self.value.title())


@dataclass
class TaskProgress:
    """Progress state for a task."""
    task_id: str
    task_name: str
    stage: TaskStage
    stage_message: str = ""
    started_at: str = ""
    updated_at: str = ""
    progress_percent: int = 0
    retro: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "stage": self.stage.value,
            "stage_emoji": self.stage.emoji,
            "stage_display": self.stage.display_name,
            "stage_message": self.stage_message,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "progress_percent": self.progress_percent,
            "retro": self.retro,
            "error": self.error
        }


class TaskProgressTracker:
    """
    Tracks task progress and emits updates via callbacks.

    Usage:
        tracker = TaskProgressTracker(emit_callback)
        tracker.start_task("task-123", "Add user login")
        tracker.update_stage(TaskStage.ANALYZING, "Reading codebase")
        tracker.update_stage(TaskStage.IMPLEMENTING, "Writing auth module")
        tracker.complete_task("Implemented JWT auth. Added unit tests for all flows.")
    """

    def __init__(self, emit_callback: Optional[Callable[[Dict], None]] = None):
        self.emit_callback = emit_callback
        self.current_tasks: Dict[str, TaskProgress] = {}
        self._lock = threading.Lock()

    def start_task(self, task_id: str, task_name: str) -> TaskProgress:
        """Start tracking a new task."""
        now = datetime.now().isoformat()
        progress = TaskProgress(
            task_id=task_id,
            task_name=task_name,
            stage=TaskStage.STARTING,
            stage_message="Picking up task...",
            started_at=now,
            updated_at=now,
            progress_percent=5
        )

        with self._lock:
            self.current_tasks[task_id] = progress

        self._emit_update(progress)
        return progress

    def update_stage(self, task_id: str, stage: TaskStage, message: str = ""):
        """Update task stage."""
        with self._lock:
            if task_id not in self.current_tasks:
                return
            progress = self.current_tasks[task_id]

        # Calculate progress percentage based on stage
        stage_progress = {
            TaskStage.STARTING: 5,
            TaskStage.ANALYZING: 15,
            TaskStage.PLANNING: 30,
            TaskStage.IMPLEMENTING: 60,
            TaskStage.TESTING: 80,
            TaskStage.REVIEWING: 90,
            TaskStage.COMPLETED: 100,
            TaskStage.FAILED: 0
        }

        progress.stage = stage
        progress.stage_message = message or f"{stage.display_name}..."
        progress.updated_at = datetime.now().isoformat()
        progress.progress_percent = stage_progress.get(stage, 50)

        self._emit_update(progress)

    def complete_task(self, task_id: str, retro: str):
        """Complete a task with a 2-sentence retrospective."""
        with self._lock:
            if task_id not in self.current_tasks:
                return
            progress = self.current_tasks[task_id]

        progress.stage = TaskStage.COMPLETED
        progress.stage_message = "Task completed successfully"
        progress.updated_at = datetime.now().isoformat()
        progress.progress_percent = 100
        progress.retro = retro

        self._emit_update(progress)

        # Clean up after delay
        def cleanup():
            time.sleep(30)  # Keep in list for 30 seconds
            with self._lock:
                self.current_tasks.pop(task_id, None)

        threading.Thread(target=cleanup, daemon=True).start()

    def fail_task(self, task_id: str, error: str):
        """Mark task as failed."""
        with self._lock:
            if task_id not in self.current_tasks:
                return
            progress = self.current_tasks[task_id]

        progress.stage = TaskStage.FAILED
        progress.stage_message = "Task failed"
        progress.updated_at = datetime.now().isoformat()
        progress.error = error

        self._emit_update(progress)

    def get_all_progress(self) -> list:
        """Get all current task progress."""
        with self._lock:
            return [p.to_dict() for p in self.current_tasks.values()]

    def _emit_update(self, progress: TaskProgress):
        """Emit progress update via callback."""
        if self.emit_callback:
            try:
                self.emit_callback({
                    "type": "task:progress",
                    "data": progress.to_dict()
                })
            except Exception as e:
                print(f"[TaskProgress] Emit error: {e}")


# Stage detection from Claude output
STAGE_PATTERNS = {
    TaskStage.ANALYZING: [
        "let me read", "reading", "examining", "looking at", "checking",
        "understanding", "analyzing", "reviewing the code", "let me understand"
    ],
    TaskStage.PLANNING: [
        "i'll need to", "the plan is", "i will", "planning to", "approach:",
        "steps:", "first,", "let me plan", "strategy"
    ],
    TaskStage.IMPLEMENTING: [
        "creating", "writing", "adding", "implementing", "let me write",
        "edit tool", "write tool", "modifying", "updating"
    ],
    TaskStage.TESTING: [
        "running tests", "testing", "npm test", "pytest", "go test",
        "verifying", "checking if", "make sure"
    ],
    TaskStage.REVIEWING: [
        "looks good", "review", "final check", "everything is", "completed",
        "summarizing", "recap", "done with"
    ]
}


def detect_stage_from_output(output: str) -> Optional[TaskStage]:
    """Detect task stage from Claude's output."""
    output_lower = output.lower()

    for stage, patterns in STAGE_PATTERNS.items():
        for pattern in patterns:
            if pattern in output_lower:
                return stage

    return None


def generate_auto_retro(task_name: str, output_summary: str) -> str:
    """
    Generate a 2-sentence retrospective from task output.

    This is a simple heuristic - ideally Claude would generate this.
    """
    # Extract key actions (simple heuristic)
    actions = []
    if "created" in output_summary.lower() or "added" in output_summary.lower():
        actions.append("Added new functionality")
    if "fixed" in output_summary.lower() or "bug" in output_summary.lower():
        actions.append("Fixed issues")
    if "test" in output_summary.lower():
        actions.append("Verified with tests")
    if "refactor" in output_summary.lower():
        actions.append("Improved code structure")

    action_str = actions[0] if actions else "Completed the implementation"

    # Second sentence about outcome
    if "passing" in output_summary.lower() or "success" in output_summary.lower():
        outcome = "All checks pass."
    elif "error" in output_summary.lower():
        outcome = "Some issues need attention."
    else:
        outcome = "Ready for review."

    return f"{action_str} for '{task_name}'. {outcome}"
