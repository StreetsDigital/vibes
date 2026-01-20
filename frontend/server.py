#!/usr/bin/env python3
"""
Vibes Frontend Server
=====================

Simple Flask server that:
1. Serves the Kanban UI
2. Provides REST API for Beads
3. Proxies chat to Claude

Run:
    python frontend/server.py --project /path/to/project

Or with Docker:
    docker compose up frontend
"""

import os
import sys
import json
import subprocess
import asyncio
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, Response

# Add mcp_server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

from gastown_integration import BeadStore, Bead, BeadStatus, Mayor

app = Flask(__name__, static_folder='.')

# Global state
_project_dir: Path = None
_bead_store: BeadStore = None
_mayor: Mayor = None

# Auth config (set via environment or args)
AUTH_USERNAME = os.environ.get("VIBES_USERNAME", "")
AUTH_PASSWORD = os.environ.get("VIBES_PASSWORD", "")


def check_auth(username: str, password: str) -> bool:
    """Check if username/password is valid."""
    if not AUTH_USERNAME or not AUTH_PASSWORD:
        return True  # No auth configured
    return secrets.compare_digest(username, AUTH_USERNAME) and \
           secrets.compare_digest(password, AUTH_PASSWORD)


def authenticate():
    """Send 401 response for authentication."""
    return Response(
        'Authentication required',
        401,
        {'WWW-Authenticate': 'Basic realm="Vibes"'}
    )


def requires_auth(f):
    """Decorator for routes that require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if AUTH_USERNAME and AUTH_PASSWORD:
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
        return f(*args, **kwargs)
    return decorated


def init_app(project_dir: str):
    """Initialize the app with a project directory."""
    global _project_dir, _bead_store, _mayor

    _project_dir = Path(project_dir)
    _bead_store = BeadStore(_project_dir, auto_commit=True)
    _mayor = Mayor(_project_dir)

    print(f"[vibes-frontend] Initialized for project: {_project_dir}")
    print(f"[vibes-frontend] Beads directory: {_bead_store.beads_dir}")


# ===========================================
# Static Files
# ===========================================

@app.route('/')
@requires_auth
def index():
    """Serve the main UI."""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
@requires_auth
def static_files(path):
    """Serve static files."""
    return send_from_directory('.', path)


# ===========================================
# Board API
# ===========================================

@app.route('/api/board')
@requires_auth
def get_board():
    """Get the Kanban board state."""
    if not _bead_store:
        return jsonify({"error": "Not initialized"}), 500

    beads = _bead_store.load_all()

    # Group by status
    board = {
        "todo": [],
        "in_progress": [],
        "review": [],
        "done": []
    }

    status_map = {
        "pending": "todo",
        "in_progress": "in_progress",
        "needs_review": "review",
        "passing": "done"
    }

    for bead in beads:
        status = bead.status.value if isinstance(bead.status, BeadStatus) else bead.status
        column = status_map.get(status, "todo")
        board[column].append(bead.to_feature_dict())

    # Sort by priority (descending)
    for column in board.values():
        column.sort(key=lambda x: x.get("priority", 0), reverse=True)

    return jsonify({
        "board": board,
        "stats": _bead_store.get_stats()
    })


@app.route('/api/task', methods=['POST'])
@requires_auth
def create_task():
    """Create a new task."""
    if not _mayor:
        return jsonify({"error": "Not initialized"}), 500

    data = request.json
    bead = _mayor.create_bead(
        name=data.get("name", "Untitled"),
        description=data.get("description", ""),
        test_cases=data.get("test_cases", []),
        priority=data.get("priority", 0)
    )

    return jsonify({
        "success": True,
        "bead_id": bead.id,
        "task": bead.to_feature_dict()
    })


@app.route('/api/task/<task_id>')
@requires_auth
def get_task(task_id):
    """Get a specific task."""
    if not _bead_store:
        return jsonify({"error": "Not initialized"}), 500

    bead = _bead_store.load(task_id)
    if not bead:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(bead.to_feature_dict())


@app.route('/api/task/<task_id>/move', methods=['POST'])
@requires_auth
def move_task(task_id):
    """Move a task to a different column."""
    if not _bead_store:
        return jsonify({"error": "Not initialized"}), 500

    data = request.json
    new_status = data.get("status")

    bead = _bead_store.load(task_id)
    if not bead:
        return jsonify({"error": "Task not found"}), 404

    old_status = bead.status
    bead.status = new_status
    _bead_store.save(bead, f"Move {bead.name}: {old_status} -> {new_status}")

    return jsonify({
        "success": True,
        "bead_id": task_id,
        "old_status": old_status,
        "new_status": new_status
    })


@app.route('/api/task/<task_id>', methods=['DELETE'])
@requires_auth
def delete_task(task_id):
    """Delete a task."""
    if not _bead_store:
        return jsonify({"error": "Not initialized"}), 500

    result = _bead_store.delete(task_id)
    return jsonify(result)


# ===========================================
# Chat API (Claude Integration)
# ===========================================

@app.route('/api/git/branch')
@requires_auth
def get_branch():
    """Get current git branch."""
    if not _project_dir:
        return jsonify({"branch": "main"})

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=str(_project_dir)
        )
        branch = result.stdout.strip() or "main"
        return jsonify({"branch": branch})
    except Exception:
        return jsonify({"branch": "main"})


@app.route('/api/chat', methods=['POST'])
@requires_auth
def chat():
    """Send a message to Claude."""
    data = request.json
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Build context from current board state
    context = build_chat_context()

    # Run Claude CLI with the message
    try:
        response = run_claude_prompt(message, context)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e), "response": f"Error: {str(e)}"}), 500


def build_chat_context() -> str:
    """Build context about current tasks for Claude."""
    if not _bead_store:
        return ""

    beads = _bead_store.load_all()
    stats = _bead_store.get_stats()

    lines = [
        "## Current Task Board",
        f"Total: {stats['total']} tasks",
        f"In Progress: {stats['in_progress']}",
        f"Pending: {stats['pending']}",
        f"Needs Review: {stats['needs_review']}",
        f"Complete: {stats['passing']}",
        ""
    ]

    # List in-progress and pending tasks
    active = [b for b in beads if b.status in ["in_progress", BeadStatus.IN_PROGRESS]]
    pending = [b for b in beads if b.status in ["pending", BeadStatus.PENDING]]

    if active:
        lines.append("### Currently Working On:")
        for b in active:
            lines.append(f"- {b.name}: {b.description or 'No description'}")
        lines.append("")

    if pending[:5]:  # Top 5 pending
        lines.append("### Next Up:")
        for b in pending[:5]:
            lines.append(f"- {b.name}")
        lines.append("")

    return "\n".join(lines)


def run_claude_prompt(message: str, context: str) -> str:
    """Run a prompt through Claude CLI."""
    full_prompt = f"""You are helping with a task board. Here's the current state:

{context}

User message: {message}

Respond helpfully and concisely."""

    try:
        # Try using Claude CLI
        result = subprocess.run(
            ["claude", "--print", "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(_project_dir)
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Claude CLI error: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Request timed out. Claude may be processing a long response."
    except FileNotFoundError:
        return "Claude CLI not found. Make sure it's installed and in PATH."
    except Exception as e:
        return f"Error running Claude: {str(e)}"


# ===========================================
# Webhook endpoints (for Polecats)
# ===========================================

@app.route('/api/webhook/polecat/started', methods=['POST'])
def polecat_started():
    """Handle Polecat started webhook."""
    data = request.json
    print(f"[webhook] Polecat started: {data.get('polecat_id')}")
    return jsonify({"status": "ok"})


@app.route('/api/webhook/polecat/progress', methods=['POST'])
def polecat_progress():
    """Handle Polecat progress webhook."""
    data = request.json
    print(f"[webhook] Polecat progress: {data.get('message')}")
    return jsonify({"status": "ok"})


@app.route('/api/webhook/polecat/completed', methods=['POST'])
def polecat_completed():
    """Handle Polecat completed webhook."""
    data = request.json
    print(f"[webhook] Polecat completed: {data.get('polecat_id')}")

    # Refresh beads from git (Polecat may have pushed changes)
    if _project_dir:
        subprocess.run(["git", "pull", "--rebase"], cwd=str(_project_dir), capture_output=True)

    return jsonify({"status": "ok"})


# ===========================================
# Main
# ===========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vibes Frontend Server")
    parser.add_argument("--project", "-p", type=str, default=".",
                        help="Project directory (default: current)")
    parser.add_argument("--port", type=int, default=3000,
                        help="Port to listen on (default: 3000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")

    args = parser.parse_args()

    # Initialize
    project_dir = Path(args.project).resolve()
    if not project_dir.exists():
        print(f"Error: Project directory does not exist: {project_dir}")
        sys.exit(1)

    # Check if it's a git repo
    if not (project_dir / ".git").exists():
        print(f"Error: Not a git repository: {project_dir}")
        sys.exit(1)

    init_app(str(project_dir))

    print(f"[vibes-frontend] Starting server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)
