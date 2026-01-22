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

# Serve from React build (frontend-react/dist)
STATIC_DIR = Path(__file__).parent.parent / "frontend-react" / "dist"
app = Flask(__name__, static_folder=str(STATIC_DIR))

# Global state
_project_dir: Path = None
_bead_store: BeadStore = None
_mayor: Mayor = None
_projects_root: Path = None  # Root directory containing all projects
_current_claude_process: subprocess.Popen = None  # Track current Claude process for stop functionality

# Auth config (set via environment or args)
AUTH_USERNAME = os.environ.get("VIBES_USERNAME", "")
AUTH_PASSWORD = os.environ.get("VIBES_PASSWORD", "")

# Autonomous mode system prompt
AUTONOMOUS_SYSTEM_PROMPT = """You are an autonomous coding agent with a team of specialized subagents. You have MCP tools for task management and coding.

## AVAILABLE MCP TOOLS:
- `kanban_get_board` - Get current board state with all tasks
- `kanban_move_task` - Move task: {"bead_id": "...", "column": "in_progress|done|todo"}
- `kanban_create_task` - Create task: {"name": "...", "description": "...", "test_cases": [...]}
- `subagent_spawn` - Spawn parallel agent for a feature: {"feature": {...}}
- `feature_discuss` - Pre-planning discussion for complex features
- `aleph_search` - Search codebase for relevant code

## AUTONOMOUS WORKFLOW:
1. Use `kanban_get_board` to see pending tasks
2. Pick the HIGHEST PRIORITY task from todo column
3. Use `kanban_move_task` to move it to "in_progress"
4. Implement the feature - write real code, create files, run tests
5. Use `kanban_move_task` to move it to "done" when complete
6. Repeat from step 1 until no tasks remain

## AGENT TYPES (spawn via subagent_spawn with agent_type):

### CODING AGENTS:
- `feature_agent` - Implements features, writes business logic
- `refactor_agent` - Refactors code, improves architecture

### E2E TESTING AGENTS:
- `e2e_test_agent` - Writes end-to-end tests (Playwright, Cypress, etc.)
- `integration_test_agent` - Writes integration tests, API tests
- `unit_test_agent` - Writes unit tests for individual functions
- `test_runner_agent` - Runs test suites, reports failures, suggests fixes

### INFRASTRUCTURE AGENTS:
- `docker_agent` - Creates/updates Dockerfiles, docker-compose configs
- `ci_cd_agent` - Sets up GitHub Actions, GitLab CI, Jenkins pipelines
- `deployment_agent` - Creates deployment scripts, K8s manifests, Terraform
- `monitoring_agent` - Sets up logging, metrics, alerting configs
- `security_agent` - Audits code for vulnerabilities, adds security headers

### QA AGENTS:
- `code_review_agent` - Reviews code changes, suggests improvements
- `documentation_agent` - Writes READMEs, API docs, inline comments

## MULTI-AGENT STRATEGY:
1. Spawn `feature_agent` for each coding task
2. Spawn `e2e_test_agent` once features are ready
3. Spawn `docker_agent` if containerization needed
4. Spawn `ci_cd_agent` to set up pipelines
5. Use `test_runner_agent` to verify everything works

## RULES:
- DO NOT ask questions - make reasonable decisions and proceed
- DO NOT wait for approval - execute autonomously
- DO update the board as you work (move tasks through columns)
- DO write production-quality code with tests
- DO spawn specialized agents for their domains
- DO use existing code patterns from the codebase

START NOW. Get the board, analyze tasks, spawn appropriate agents, and execute."""


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


def init_app(project_dir: str, projects_root: str = None):
    """Initialize the app with a project directory."""
    global _project_dir, _bead_store, _mayor, _projects_root

    _project_dir = Path(project_dir)
    _bead_store = BeadStore(_project_dir, auto_commit=True)
    _mayor = Mayor(_project_dir)

    # Set projects root (for project switching)
    if projects_root:
        _projects_root = Path(projects_root)
    else:
        # Default to parent directory of current project
        _projects_root = _project_dir.parent

    print(f"[vibes-frontend] Initialized for project: {_project_dir}")
    print(f"[vibes-frontend] Projects root: {_projects_root}")
    print(f"[vibes-frontend] Beads directory: {_bead_store.beads_dir}")


# ===========================================
# Static Files
# ===========================================

@app.route('/')
@requires_auth
def index():
    """Serve the main UI."""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/<path:path>')
@requires_auth
def static_files(path):
    """Serve static files."""
    # Try to serve file from React build, fallback to index.html for SPA routing
    file_path = STATIC_DIR / path
    if file_path.exists():
        return send_from_directory(STATIC_DIR, path)
    # SPA fallback - serve index.html for client-side routing
    return send_from_directory(STATIC_DIR, 'index.html')


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


@app.route('/api/autowork', methods=['POST'])
@requires_auth
def start_autowork():
    """Start autonomous work mode - Claude works through all tasks automatically."""
    if not _project_dir:
        return jsonify({"error": "Not initialized"}), 500

    data = request.json or {}
    parallel_agents = data.get("parallel_agents", 1)  # Number of parallel agents to spawn

    # Run autonomous Claude in background
    import threading

    def run_autonomous():
        try:
            run_autonomous_claude(parallel_agents)
        except Exception as e:
            print(f"[autowork] Error: {e}")

    thread = threading.Thread(target=run_autonomous, daemon=True)
    thread.start()

    return jsonify({
        "success": True,
        "message": f"Autonomous mode started with {parallel_agents} agent(s)",
        "parallel_agents": parallel_agents
    })


# ===========================================
# Session & Projects API
# ===========================================

def get_session_file() -> Path:
    """Get path to session state file."""
    if not _project_dir:
        return None
    vibes_dir = _project_dir / ".git" / "vibes"
    vibes_dir.mkdir(parents=True, exist_ok=True)
    return vibes_dir / "session.json"


def load_session() -> dict:
    """Load session state."""
    session_file = get_session_file()
    if not session_file or not session_file.exists():
        return {}
    try:
        return json.loads(session_file.read_text())
    except:
        return {}


def save_session(data: dict):
    """Save session state."""
    session_file = get_session_file()
    if session_file:
        session_file.write_text(json.dumps(data, indent=2))


@app.route('/api/session/ping', methods=['POST'])
@requires_auth
def session_ping():
    """Record activity and return session summary if returning after inactivity."""
    session = load_session()
    now = datetime.now()
    last_activity = session.get("last_activity")

    # Calculate time since last activity
    hours_inactive = 0
    if last_activity:
        try:
            last_dt = datetime.fromisoformat(last_activity)
            hours_inactive = (now - last_dt).total_seconds() / 3600
        except:
            pass

    # Update last activity
    session["last_activity"] = now.isoformat()
    save_session(session)

    # If inactive for 2+ hours, generate summary
    summary = None
    if hours_inactive >= 2:
        summary = generate_session_summary(hours_inactive)

    return jsonify({
        "hours_inactive": round(hours_inactive, 1),
        "summary": summary
    })


def generate_session_summary(hours_inactive: float) -> str:
    """Generate a welcome-back summary."""
    lines = [f"Welcome back! You were away for {hours_inactive:.1f} hours."]
    lines.append("")

    # Board state
    if _bead_store:
        stats = _bead_store.get_stats()
        beads = _bead_store.load_all()

        lines.append(f"**Board Status:** {stats['passing']}/{stats['total']} tasks complete")

        # In progress
        active = [b for b in beads if str(b.status) in ["in_progress", "BeadStatus.IN_PROGRESS"]]
        if active:
            lines.append("")
            lines.append("**In Progress:**")
            for b in active[:3]:
                lines.append(f"- {b.name}")

        # Needs review
        review = [b for b in beads if str(b.status) in ["needs_review", "BeadStatus.NEEDS_REVIEW"]]
        if review:
            lines.append("")
            lines.append("**Needs Review:**")
            for b in review[:3]:
                lines.append(f"- {b.name}")

    # Recent chat
    chat_history = load_chat_history()
    if chat_history:
        recent = chat_history[-2:]  # Last exchange
        if recent:
            lines.append("")
            lines.append("**Last conversation:**")
            for msg in recent:
                role = "You" if msg["role"] == "user" else "Claude"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                lines.append(f"- {role}: {content}")

    return "\n".join(lines)


@app.route('/api/projects')
@requires_auth
def list_projects():
    """List available projects."""
    projects = []

    # Current project
    if _project_dir:
        projects.append({
            "name": _project_dir.name,
            "path": str(_project_dir),
            "current": True
        })

    # Look for other projects in projects root
    if _projects_root and _projects_root.exists():
        for p in _projects_root.iterdir():
            if p.is_dir() and (p / ".git").exists() and p != _project_dir:
                projects.append({
                    "name": p.name,
                    "path": str(p),
                    "current": False
                })

    return jsonify({"projects": projects})


@app.route('/api/projects/switch', methods=['POST'])
@requires_auth
def switch_project():
    """Switch to a different project."""
    global _project_dir, _bead_store, _mayor

    data = request.json
    project_path = data.get("path")

    if not project_path:
        return jsonify({"error": "No project path provided"}), 400

    new_project = Path(project_path)
    if not new_project.exists() or not (new_project / ".git").exists():
        return jsonify({"error": "Invalid project path"}), 400

    # Switch
    _project_dir = new_project
    _bead_store = BeadStore(_project_dir, auto_commit=True)
    _mayor = Mayor(_project_dir)

    return jsonify({
        "success": True,
        "project": _project_dir.name,
        "path": str(_project_dir)
    })


# ===========================================
# Chat API (Claude Integration)
# ===========================================

def get_chat_file() -> Path:
    """Get path to chat history file."""
    if not _project_dir:
        return None
    vibes_dir = _project_dir / ".git" / "vibes"
    vibes_dir.mkdir(parents=True, exist_ok=True)
    return vibes_dir / "chat.json"


def load_chat_history() -> list:
    """Load chat history from file."""
    chat_file = get_chat_file()
    if not chat_file or not chat_file.exists():
        return []
    try:
        return json.loads(chat_file.read_text())
    except:
        return []


def save_chat_history(messages: list):
    """Save chat history to file."""
    chat_file = get_chat_file()
    if chat_file:
        chat_file.write_text(json.dumps(messages, indent=2))


@app.route('/api/chat/history')
@requires_auth
def get_chat_history():
    """Get chat history."""
    messages = load_chat_history()
    return jsonify({"messages": messages})


@app.route('/api/chat/history', methods=['DELETE'])
@requires_auth
def clear_chat_history():
    """Clear chat history."""
    save_chat_history([])
    return jsonify({"success": True})


@app.route('/api/chat/stop', methods=['POST'])
@requires_auth
def stop_chat():
    """Stop the current Claude generation."""
    global _current_claude_process

    if _current_claude_process is not None:
        try:
            _current_claude_process.kill()
            return jsonify({"success": True, "message": "Stopped"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    else:
        return jsonify({"success": True, "message": "No active process"})


@app.route('/api/logs')
@requires_auth
def get_claude_logs():
    """Get Claude debug logs."""
    import re
    from pathlib import Path

    filter_type = request.args.get('filter', 'all')
    limit = int(request.args.get('limit', 200))

    debug_dir = Path.home() / '.claude' / 'debug'
    logs = []

    if debug_dir.exists():
        # Get most recent debug files
        debug_files = sorted(debug_dir.glob('*.txt'), key=lambda f: f.stat().st_mtime, reverse=True)[:5]

        for debug_file in debug_files:
            try:
                content = debug_file.read_text()
                for line in content.split('\n'):
                    if not line.strip():
                        continue

                    # Parse log line: 2026-01-21T10:49:59.077Z [LEVEL] message
                    match = re.match(r'^(\d{4}-\d{2}-\d{2}T[\d:.]+Z)\s+\[(\w+)\]\s+(.*)$', line)
                    if match:
                        timestamp, level, message = match.groups()
                        level = level.lower()
                        source = 'claude'

                        # Categorize by content
                        if 'mcp' in message.lower():
                            source = 'claude'
                        elif 'statsig' in message.lower() or 'gate' in message.lower():
                            source = 'system'
                        elif 'error' in level:
                            source = 'system'

                        # Apply filter
                        if filter_type == 'error' and level != 'error':
                            continue
                        elif filter_type == 'claude' and source != 'claude':
                            continue
                        elif filter_type == 'system' and source != 'system':
                            continue

                        logs.append({
                            'id': f"{debug_file.stem}_{len(logs)}",
                            'timestamp': timestamp,
                            'level': level if level in ['info', 'warn', 'error', 'debug'] else 'info',
                            'source': source,
                            'message': message[:500]  # Truncate long messages
                        })
            except Exception as e:
                print(f"[logs] Error reading {debug_file}: {e}")

    # Sort by timestamp and limit
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    logs = logs[:limit]
    logs.reverse()  # Oldest first for display

    return jsonify({"logs": logs})


@app.route('/api/logs', methods=['DELETE'])
@requires_auth
def clear_claude_logs():
    """Clear Claude debug logs."""
    from pathlib import Path

    debug_dir = Path.home() / '.claude' / 'debug'

    if debug_dir.exists():
        for debug_file in debug_dir.glob('*.txt'):
            try:
                debug_file.unlink()
            except Exception as e:
                print(f"[logs] Error deleting {debug_file}: {e}")

    return jsonify({"success": True})


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

    # Load existing history
    history = load_chat_history()

    # Add user message
    history.append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat()
    })

    # Build context from current board state
    context = build_chat_context()

    # Run Claude CLI with the message and history
    try:
        response = run_claude_prompt(message, context, history[:-1])  # Pass history excluding current message

        # Add assistant response
        history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        # Save history (keep last 100 messages)
        save_chat_history(history[-100:])

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


def run_claude_prompt(message: str, context: str, history: list = None) -> str:
    """Run a prompt through Claude CLI."""
    global _current_claude_process

    # Build conversation history (last 6 messages, truncated to save tokens)
    history_text = ""
    if history:
        recent = history[-6:]  # Keep last 6 messages (3 exchanges)
        history_lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg['content']
            # Truncate long messages to 300 chars
            if len(content) > 300:
                content = content[:300] + "..."
            history_lines.append(f"{role}: {content}")
        if history_lines:
            history_text = "\n\n## Recent Conversation:\n" + "\n\n".join(history_lines)

    full_prompt = f"""You are helping with a task board. Here's the current state:

{context}{history_text}

User message: {message}

Respond helpfully and concisely."""

    try:
        # Write prompt to temp file to avoid shell escaping issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(full_prompt)
            prompt_file = f.name
        os.chmod(prompt_file, 0o644)  # Make readable by vibes user

        # Use Popen for interruptibility
        # Run as vibes user (non-root) so --dangerously-skip-permissions works
        # --dangerously-skip-permissions allows autonomous operation without approval prompts
        # --mcp-config loads MCP servers (context7, etc.) for enhanced capabilities
        # runuser doesn't require password when running as root
        mcp_config = "/home/vibes/.claude/settings.json"
        cmd = f'runuser -u vibes -- bash -c \'cd "{_project_dir}" && claude --print --dangerously-skip-permissions --mcp-config {mcp_config} -p "$(cat {prompt_file})"\''
        _current_claude_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(_project_dir),
            env={**os.environ, "HOME": "/home/vibes"},
            shell=True
        )

        try:
            stdout, stderr = _current_claude_process.communicate(timeout=120)

            if _current_claude_process.returncode == 0:
                return stdout.strip()
            elif _current_claude_process.returncode == -9:  # Killed
                return "*(Stopped by user)*"
            else:
                return f"Claude CLI error: {stderr}"
        except subprocess.TimeoutExpired:
            _current_claude_process.kill()
            _current_claude_process.communicate()
            return "Request timed out. Claude may be processing a long response."
        finally:
            _current_claude_process = None
            # Clean up temp file
            try:
                os.unlink(prompt_file)
            except:
                pass

    except FileNotFoundError:
        _current_claude_process = None
        return "Claude CLI not found. Make sure it's installed and in PATH."
    except Exception as e:
        _current_claude_process = None
        return f"Error running Claude: {str(e)}"


def run_autonomous_claude(parallel_agents: int = 1):
    """Run Claude in autonomous mode - works through all tasks on the board."""
    import tempfile
    import time

    print(f"[autowork] Starting autonomous mode with {parallel_agents} agent(s)")

    # Add starting message to chat immediately
    history = load_chat_history()
    history.append({
        "role": "user",
        "content": f"[AUTO] Start autonomous mode with {parallel_agents} parallel agent(s)",
        "timestamp": datetime.now().isoformat()
    })
    history.append({
        "role": "assistant",
        "content": f"🤖 **Autonomous mode activated!**\n\nI'm checking the kanban board and will work through all pending tasks.\n\n*Working with {parallel_agents} parallel agent(s)...*",
        "timestamp": datetime.now().isoformat()
    })
    save_chat_history(history[-100:])

    # Build the autonomous prompt
    prompt = AUTONOMOUS_SYSTEM_PROMPT

    if parallel_agents > 1:
        prompt += f"\n\n## PARALLEL MODE: Spawn up to {parallel_agents} subagents to work on tasks concurrently."

    # Write prompt to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        prompt_file = f.name
    os.chmod(prompt_file, 0o644)

    mcp_config = "/home/vibes/.claude/settings.json"

    # Run Claude with longer timeout for autonomous work (10 minutes)
    cmd = f'runuser -u vibes -- bash -c \'cd "{_project_dir}" && claude --print --dangerously-skip-permissions --mcp-config {mcp_config} -p "$(cat {prompt_file})"\''

    print(f"[autowork] Running: {cmd[:100]}...")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            text=True,
            cwd=str(_project_dir),
            env={**os.environ, "HOME": "/home/vibes"},
            shell=True,
            bufsize=1  # Line buffered
        )

        # Stream output and update chat periodically
        output_lines = []
        last_update = time.time()
        update_interval = 10  # Update chat every 10 seconds

        for line in iter(process.stdout.readline, ''):
            output_lines.append(line)
            print(f"[autowork] {line.rstrip()}")

            # Periodic update to chat
            if time.time() - last_update > update_interval:
                last_update = time.time()
                # Add progress update to chat
                history = load_chat_history()
                progress_text = ''.join(output_lines[-20:])  # Last 20 lines
                history.append({
                    "role": "assistant",
                    "content": f"📝 **Progress update:**\n```\n{progress_text[-1000:]}\n```",
                    "timestamp": datetime.now().isoformat()
                })
                save_chat_history(history[-100:])

        process.wait(timeout=600)
        stdout = ''.join(output_lines)

        if process.returncode == 0:
            print(f"[autowork] Completed successfully")

            # Save final output to chat history
            history = load_chat_history()
            history.append({
                "role": "assistant",
                "content": f"✅ **Autonomous work complete!**\n\n{stdout[-2000:] if len(stdout) > 2000 else stdout}",
                "timestamp": datetime.now().isoformat()
            })
            save_chat_history(history[-100:])
        else:
            print(f"[autowork] Error: returncode={process.returncode}")
            history = load_chat_history()
            history.append({
                "role": "assistant",
                "content": f"❌ **Autonomous work failed**\n\nError code: {process.returncode}\n\n```\n{stdout[-1000:]}\n```",
                "timestamp": datetime.now().isoformat()
            })
            save_chat_history(history[-100:])

    except subprocess.TimeoutExpired:
        process.kill()
        print("[autowork] Timed out after 10 minutes")
        history = load_chat_history()
        history.append({
            "role": "assistant",
            "content": "⏱️ **Autonomous work timed out** after 10 minutes. Check the board for progress.",
            "timestamp": datetime.now().isoformat()
        })
        save_chat_history(history[-100:])
    except Exception as e:
        print(f"[autowork] Exception: {e}")
        history = load_chat_history()
        history.append({
            "role": "assistant",
            "content": f"❌ **Error:** {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
        save_chat_history(history[-100:])
    finally:
        try:
            os.unlink(prompt_file)
        except:
            pass


# ===========================================
# Claude Settings API (MCP, Skills, Agents)
# ===========================================

def get_claude_settings_paths() -> dict:
    """Get paths to Claude settings files."""
    home = Path.home()
    return {
        "global": home / ".claude" / "settings.json",
        "project": _project_dir / ".claude" / "settings.json" if _project_dir else None,
        "skills_global": home / ".claude" / "skills",
        "skills_project": _project_dir / ".claude" / "skills" if _project_dir else None,
    }


def load_claude_settings(scope: str = "global") -> dict:
    """Load Claude settings from file."""
    paths = get_claude_settings_paths()
    path = paths.get(scope)
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except:
        return {}


def save_claude_settings(settings: dict, scope: str = "global"):
    """Save Claude settings to file."""
    paths = get_claude_settings_paths()
    path = paths.get(scope)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2))


@app.route('/api/claude/mcp')
@requires_auth
def get_mcp_servers():
    """Get configured MCP servers."""
    global_settings = load_claude_settings("global")
    project_settings = load_claude_settings("project")

    servers = []

    # Global MCP servers
    for name, config in global_settings.get("mcpServers", {}).items():
        servers.append({
            "name": name,
            "scope": "global",
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "enabled": not config.get("disabled", False)
        })

    # Project MCP servers
    for name, config in project_settings.get("mcpServers", {}).items():
        servers.append({
            "name": name,
            "scope": "project",
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "enabled": not config.get("disabled", False)
        })

    return jsonify({"servers": servers})


@app.route('/api/claude/mcp', methods=['POST'])
@requires_auth
def add_mcp_server():
    """Add a new MCP server."""
    data = request.json
    name = data.get("name")
    command = data.get("command")
    args = data.get("args", [])
    scope = data.get("scope", "project")

    if not name or not command:
        return jsonify({"error": "Name and command required"}), 400

    settings = load_claude_settings(scope)
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    settings["mcpServers"][name] = {
        "command": command,
        "args": args
    }

    save_claude_settings(settings, scope)
    return jsonify({"success": True, "name": name})


@app.route('/api/claude/mcp/<name>/toggle', methods=['POST'])
@requires_auth
def toggle_mcp_server(name):
    """Toggle an MCP server on/off."""
    data = request.json
    scope = data.get("scope", "project")
    enabled = data.get("enabled", True)

    settings = load_claude_settings(scope)
    if "mcpServers" in settings and name in settings["mcpServers"]:
        if enabled:
            settings["mcpServers"][name].pop("disabled", None)
        else:
            settings["mcpServers"][name]["disabled"] = True
        save_claude_settings(settings, scope)
        return jsonify({"success": True, "enabled": enabled})

    return jsonify({"error": "Server not found"}), 404


@app.route('/api/claude/mcp/<name>', methods=['GET'])
@requires_auth
def get_mcp_server(name):
    """Get a single MCP server's details."""
    data = request.args
    scope = data.get("scope", "project")

    settings = load_claude_settings(scope)
    if "mcpServers" in settings and name in settings["mcpServers"]:
        config = settings["mcpServers"][name]
        return jsonify({
            "name": name,
            "scope": scope,
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "env": config.get("env", {}),
            "enabled": not config.get("disabled", False)
        })

    return jsonify({"error": "Server not found"}), 404


@app.route('/api/claude/mcp/<name>', methods=['PUT'])
@requires_auth
def update_mcp_server(name):
    """Update an MCP server."""
    data = request.json
    scope = data.get("scope", "project")
    new_name = data.get("name", name)
    command = data.get("command")
    args = data.get("args", [])
    env = data.get("env", {})

    settings = load_claude_settings(scope)
    if "mcpServers" not in settings or name not in settings["mcpServers"]:
        return jsonify({"error": "Server not found"}), 404

    # Get existing config
    config = settings["mcpServers"][name]

    # If renaming, delete old entry
    if new_name != name:
        del settings["mcpServers"][name]

    # Update config
    settings["mcpServers"][new_name] = {
        "command": command or config.get("command", ""),
        "args": args if args else config.get("args", []),
    }
    if env:
        settings["mcpServers"][new_name]["env"] = env
    if config.get("disabled"):
        settings["mcpServers"][new_name]["disabled"] = True

    save_claude_settings(settings, scope)
    return jsonify({"success": True, "name": new_name})


@app.route('/api/claude/mcp/<name>', methods=['DELETE'])
@requires_auth
def delete_mcp_server(name):
    """Delete an MCP server."""
    data = request.json or {}
    scope = data.get("scope", "project")

    settings = load_claude_settings(scope)
    if "mcpServers" in settings and name in settings["mcpServers"]:
        del settings["mcpServers"][name]
        save_claude_settings(settings, scope)
        return jsonify({"success": True})

    return jsonify({"error": "Server not found"}), 404


@app.route('/api/claude/skills')
@requires_auth
def get_skills():
    """Get available skills."""
    paths = get_claude_settings_paths()
    skills = []

    # Check both global and project skills directories
    for scope, skills_dir in [("global", paths["skills_global"]), ("project", paths["skills_project"])]:
        if skills_dir and skills_dir.exists():
            for skill_file in skills_dir.rglob("*.md"):
                try:
                    content = skill_file.read_text()
                    # Parse frontmatter
                    name = skill_file.stem
                    description = ""
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            import re
                            name_match = re.search(r'name:\s*(.+)', parts[1])
                            desc_match = re.search(r'description:\s*(.+)', parts[1])
                            if name_match:
                                name = name_match.group(1).strip()
                            if desc_match:
                                description = desc_match.group(1).strip()

                    skills.append({
                        "name": name,
                        "file": str(skill_file),
                        "scope": scope,
                        "description": description,
                        "enabled": True  # Skills are always enabled if they exist
                    })
                except:
                    pass

    return jsonify({"skills": skills})


@app.route('/api/claude/skills', methods=['POST'])
@requires_auth
def create_skill():
    """Create a new skill."""
    data = request.json
    name = data.get("name")
    description = data.get("description", "")
    trigger = data.get("trigger", "")
    solution = data.get("solution", "")
    scope = data.get("scope", "project")

    if not name:
        return jsonify({"error": "Name required"}), 400

    paths = get_claude_settings_paths()
    skills_dir = paths[f"skills_{scope}"]
    if not skills_dir:
        return jsonify({"error": "Invalid scope"}), 400

    skills_dir.mkdir(parents=True, exist_ok=True)

    # Create skill file
    content = f"""---
name: {name}
description: {description}
author: user
version: 1.0.0
---

## Trigger
{trigger}

## Solution
{solution}

## Verification
Verify the solution works as expected.
"""

    skill_file = skills_dir / f"{name.lower().replace(' ', '-')}.md"
    skill_file.write_text(content)

    return jsonify({"success": True, "file": str(skill_file)})


@app.route('/api/claude/skills/<path:file_path>')
@requires_auth
def get_skill_content(file_path):
    """Get skill file content."""
    try:
        path = Path("/" + file_path)
        if path.exists() and path.suffix == ".md":
            return jsonify({"content": path.read_text(), "path": str(path)})
        return jsonify({"error": "Skill not found"}), 404
    except:
        return jsonify({"error": "Invalid path"}), 400


@app.route('/api/claude/skills/<path:file_path>', methods=['PUT'])
@requires_auth
def update_skill(file_path):
    """Update a skill file."""
    try:
        path = Path("/" + file_path)
        if not path.exists() or path.suffix != ".md":
            return jsonify({"error": "Skill not found"}), 404

        data = request.json
        content = data.get("content")
        if content is None:
            return jsonify({"error": "Content required"}), 400

        path.write_text(content)
        return jsonify({"success": True, "path": str(path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/claude/skills/<path:file_path>', methods=['DELETE'])
@requires_auth
def delete_skill(file_path):
    """Delete a skill file."""
    try:
        path = Path("/" + file_path)
        if not path.exists() or path.suffix != ".md":
            return jsonify({"error": "Skill not found"}), 404

        path.unlink()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Built-in tools list with detailed info
CLAUDE_TOOLS = [
    {
        "name": "Read",
        "description": "Read files from filesystem",
        "details": "Reads file contents by path. Supports reading images, PDFs, and Jupyter notebooks. Can specify line offset and limit for large files."
    },
    {
        "name": "Write",
        "description": "Write/create files",
        "details": "Creates or overwrites files. Requires reading the file first if it exists. Use for creating new files or complete rewrites."
    },
    {
        "name": "Edit",
        "description": "Make targeted edits to files",
        "details": "Performs exact string replacements in files. Use old_string to match existing content and new_string for replacement. Supports replace_all for multiple occurrences."
    },
    {
        "name": "Bash",
        "description": "Execute shell commands",
        "details": "Runs bash commands with optional timeout. Captures output. Use for git, npm, docker, and other CLI operations. Avoid for file operations (use Read/Write/Edit instead)."
    },
    {
        "name": "Glob",
        "description": "Find files by pattern",
        "details": "Fast file pattern matching. Supports patterns like '**/*.js' or 'src/**/*.ts'. Returns file paths sorted by modification time."
    },
    {
        "name": "Grep",
        "description": "Search file contents",
        "details": "Powerful regex search using ripgrep. Supports glob patterns, file type filters, context lines, and multiple output modes."
    },
    {
        "name": "Task",
        "description": "Spawn sub-agents",
        "details": "Launches specialized agents for complex tasks. Available types: Bash, Explore, Plan, general-purpose. Agents run autonomously and return results."
    },
    {
        "name": "WebFetch",
        "description": "Fetch web content",
        "details": "Fetches URL content and processes with AI. Converts HTML to markdown. Use for retrieving and analyzing web pages."
    },
    {
        "name": "WebSearch",
        "description": "Search the web",
        "details": "Performs web searches for up-to-date information. Returns search results with links. Use for current events and recent data beyond training cutoff."
    },
    {
        "name": "NotebookEdit",
        "description": "Edit Jupyter notebooks",
        "details": "Edit cells in .ipynb files. Supports replace, insert, and delete modes. Can set cell type (code or markdown)."
    },
    {
        "name": "TodoWrite",
        "description": "Track task progress",
        "details": "Creates and manages structured task lists. Track progress with pending/in_progress/completed states. Use for complex multi-step tasks."
    },
]


@app.route('/api/claude/tools')
@requires_auth
def get_tools():
    """Get Claude's built-in tools and their status."""
    global_settings = load_claude_settings("global")
    project_settings = load_claude_settings("project")

    # Merge denied tools from both scopes
    denied_global = set(global_settings.get("deniedTools", []))
    denied_project = set(project_settings.get("deniedTools", []))
    all_denied = denied_global | denied_project

    tools = []
    for tool in CLAUDE_TOOLS:
        tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "details": tool.get("details", ""),
            "enabled": tool["name"] not in all_denied,
            "denied_in": "global" if tool["name"] in denied_global else ("project" if tool["name"] in denied_project else None)
        })

    return jsonify({"tools": tools})


@app.route('/api/claude/tools/<name>')
@requires_auth
def get_tool_details(name):
    """Get detailed info about a specific tool."""
    for tool in CLAUDE_TOOLS:
        if tool["name"] == name:
            global_settings = load_claude_settings("global")
            project_settings = load_claude_settings("project")
            denied_global = set(global_settings.get("deniedTools", []))
            denied_project = set(project_settings.get("deniedTools", []))

            return jsonify({
                "name": tool["name"],
                "description": tool["description"],
                "details": tool.get("details", ""),
                "enabled": tool["name"] not in (denied_global | denied_project),
                "denied_in": "global" if tool["name"] in denied_global else ("project" if tool["name"] in denied_project else None)
            })

    return jsonify({"error": "Tool not found"}), 404


@app.route('/api/claude/tools/<name>/toggle', methods=['POST'])
@requires_auth
def toggle_tool(name):
    """Toggle a tool on/off."""
    data = request.json
    enabled = data.get("enabled", True)
    scope = data.get("scope", "project")

    settings = load_claude_settings(scope)
    denied = set(settings.get("deniedTools", []))

    if enabled:
        denied.discard(name)
    else:
        denied.add(name)

    settings["deniedTools"] = list(denied)
    save_claude_settings(settings, scope)

    return jsonify({"success": True, "enabled": enabled})


@app.route('/api/claude/hooks')
@requires_auth
def get_hooks():
    """Get configured hooks."""
    global_settings = load_claude_settings("global")
    project_settings = load_claude_settings("project")

    hooks = []

    for scope, settings in [("global", global_settings), ("project", project_settings)]:
        for hook in settings.get("hooks", []):
            hooks.append({
                "event": hook.get("event", ""),
                "command": hook.get("command", ""),
                "scope": scope
            })

    return jsonify({
        "hooks": hooks,
        "available_events": ["PreToolUse", "PostToolUse", "Notification", "Stop"]
    })


@app.route('/api/claude/hooks', methods=['POST'])
@requires_auth
def add_hook():
    """Add a new hook."""
    data = request.json
    event = data.get("event")
    command = data.get("command")
    scope = data.get("scope", "project")

    if not event or not command:
        return jsonify({"error": "Event and command required"}), 400

    settings = load_claude_settings(scope)
    if "hooks" not in settings:
        settings["hooks"] = []

    settings["hooks"].append({
        "event": event,
        "command": command
    })

    save_claude_settings(settings, scope)
    return jsonify({"success": True})


@app.route('/api/claude/hooks', methods=['DELETE'])
@requires_auth
def delete_hook():
    """Delete a hook."""
    data = request.json
    event = data.get("event")
    command = data.get("command")
    scope = data.get("scope", "project")

    settings = load_claude_settings(scope)
    hooks = settings.get("hooks", [])

    settings["hooks"] = [h for h in hooks if not (h.get("event") == event and h.get("command") == command)]
    save_claude_settings(settings, scope)

    return jsonify({"success": True})


@app.route('/api/claude/hooks', methods=['PUT'])
@requires_auth
def update_hook():
    """Update a hook."""
    data = request.json
    old_event = data.get("old_event")
    old_command = data.get("old_command")
    old_scope = data.get("old_scope", "project")

    new_event = data.get("event")
    new_command = data.get("command")
    new_scope = data.get("scope", old_scope)

    if not all([old_event, old_command, new_event, new_command]):
        return jsonify({"error": "Missing required fields"}), 400

    # If scope changed, remove from old and add to new
    if old_scope != new_scope:
        # Remove from old scope
        old_settings = load_claude_settings(old_scope)
        old_settings["hooks"] = [h for h in old_settings.get("hooks", [])
                                  if not (h.get("event") == old_event and h.get("command") == old_command)]
        save_claude_settings(old_settings, old_scope)

        # Add to new scope
        new_settings = load_claude_settings(new_scope)
        if "hooks" not in new_settings:
            new_settings["hooks"] = []
        new_settings["hooks"].append({"event": new_event, "command": new_command})
        save_claude_settings(new_settings, new_scope)
    else:
        # Same scope, update in place
        settings = load_claude_settings(old_scope)
        hooks = settings.get("hooks", [])
        for i, h in enumerate(hooks):
            if h.get("event") == old_event and h.get("command") == old_command:
                hooks[i] = {"event": new_event, "command": new_command}
                break
        settings["hooks"] = hooks
        save_claude_settings(settings, old_scope)

    return jsonify({"success": True})


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
# Agents API
# ===========================================

@app.route('/api/agents')
@requires_auth
def get_agents():
    """Get information about running agents."""
    result = {
        "subagents": [],
        "polecats": [],
        "containers": []
    }

    try:
        # Check for subagent processes
        if _project_dir:
            subagent_dir = _project_dir / ".git" / "vibes" / "subagents"
            if subagent_dir.exists():
                for pid_file in subagent_dir.glob("*.pid"):
                    try:
                        pid = int(pid_file.read_text().strip())
                        # Check if process is still running
                        import psutil
                        if psutil.pid_exists(pid):
                            proc = psutil.Process(pid)
                            create_time = datetime.fromtimestamp(proc.create_time())
                            duration = (datetime.now() - create_time).total_seconds()

                            result["subagents"].append({
                                "id": pid_file.stem,
                                "status": "running",
                                "feature_name": pid_file.stem.replace("_", " "),
                                "duration": duration
                            })
                    except:
                        # Clean up stale PID file
                        try:
                            pid_file.unlink()
                        except:
                            pass

        # Check for Docker containers (project agents)
        try:
            import docker
            docker_client = docker.from_env()
            containers = docker_client.containers.list(all=True)

            for container in containers:
                # Look for vibes project containers
                if container.name.startswith('vibes-project-'):
                    project_id = container.labels.get('vibes.project', 'unknown')
                    result["containers"].append({
                        "name": container.name,
                        "status": container.status,
                        "project_id": project_id
                    })
        except:
            # Docker not available or not accessible
            pass

        # Check for Polecat instances (Fly.io machines)
        # This would typically query the Fly.io API or check local state files
        polecat_state_dir = Path.home() / ".vibes" / "polecats"
        if polecat_state_dir.exists():
            for state_file in polecat_state_dir.glob("*.json"):
                try:
                    state = json.loads(state_file.read_text())
                    result["polecats"].append({
                        "id": state.get("id", state_file.stem),
                        "machine_id": state.get("machine_id", "unknown"),
                        "status": state.get("status", "unknown"),
                        "convoy_id": state.get("convoy_id", "unknown")
                    })
                except:
                    pass

    except Exception as e:
        print(f"[agents-api] Error gathering agent info: {e}")

    return jsonify(result)


# ===========================================
# Quick Actions API
# ===========================================

@app.route('/api/skills/commit', methods=['POST'])
@requires_auth
def run_commit_skill():
    """Run the commit skill."""
    if not _project_dir:
        return jsonify({"error": "No project directory"}), 500

    try:
        # Run Claude with the /commit skill
        result = subprocess.run(
            ["claude", "code", "/commit"],
            capture_output=True,
            text=True,
            cwd=str(_project_dir),
            timeout=300
        )

        if result.returncode == 0:
            return jsonify({"success": True, "output": result.stdout})
        else:
            return jsonify({"error": f"Commit failed: {result.stderr}"}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Commit operation timed out"}), 500
    except FileNotFoundError:
        return jsonify({"error": "Claude CLI not found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/skills/retrospective', methods=['POST'])
@requires_auth
def run_retrospective_skill():
    """Run the retrospective skill."""
    if not _project_dir:
        return jsonify({"error": "No project directory"}), 500

    try:
        # Run Claude with the /retrospective skill
        result = subprocess.run(
            ["claude", "code", "/retrospective"],
            capture_output=True,
            text=True,
            cwd=str(_project_dir),
            timeout=300
        )

        if result.returncode == 0:
            return jsonify({"success": True, "output": result.stdout})
        else:
            return jsonify({"error": f"Retrospective failed: {result.stderr}"}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Retrospective operation timed out"}), 500
    except FileNotFoundError:
        return jsonify({"error": "Claude CLI not found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/git/create-pr', methods=['POST'])
@requires_auth
def create_pull_request():
    """Create a pull request using git CLI."""
    if not _project_dir:
        return jsonify({"error": "No project directory"}), 500

    try:
        # Check if gh CLI is available
        subprocess.run(["gh", "--version"], capture_output=True, check=True)

        # Get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=str(_project_dir)
        )
        current_branch = branch_result.stdout.strip()

        if not current_branch or current_branch == "main" or current_branch == "master":
            return jsonify({"error": "Cannot create PR from main/master branch"}), 400

        # Create PR using gh CLI
        pr_result = subprocess.run(
            ["gh", "pr", "create", "--fill"],
            capture_output=True,
            text=True,
            cwd=str(_project_dir),
            timeout=60
        )

        if pr_result.returncode == 0:
            return jsonify({"success": True, "output": pr_result.stdout.strip()})
        else:
            return jsonify({"error": f"PR creation failed: {pr_result.stderr}"}), 500

    except FileNotFoundError:
        return jsonify({"error": "GitHub CLI (gh) not found. Please install it first."}), 500
    except subprocess.CalledProcessError:
        return jsonify({"error": "GitHub CLI not available or not authenticated"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/quality/check', methods=['POST'])
@requires_auth
def run_quality_checks():
    """Run quality checks using quality gate tools."""
    if not _project_dir:
        return jsonify({"error": "No project directory"}), 500

    try:
        # Try to run quality_check via MCP/Claude if available
        quality_result = subprocess.run(
            ["claude", "code", "/verify"],
            capture_output=True,
            text=True,
            cwd=str(_project_dir),
            timeout=180
        )

        if quality_result.returncode == 0:
            return jsonify({"success": True, "output": quality_result.stdout})
        else:
            # Fall back to basic checks
            checks = []

            # Run basic linting/type checks if tools are available
            try:
                # Try npm run lint
                lint_result = subprocess.run(
                    ["npm", "run", "lint"],
                    capture_output=True,
                    text=True,
                    cwd=str(_project_dir),
                    timeout=60
                )
                checks.append(f"Lint: {'✅ Passed' if lint_result.returncode == 0 else '❌ Failed'}")

                # Try npm run type-check
                type_result = subprocess.run(
                    ["npm", "run", "type-check"],
                    capture_output=True,
                    text=True,
                    cwd=str(_project_dir),
                    timeout=60
                )
                checks.append(f"Types: {'✅ Passed' if type_result.returncode == 0 else '❌ Failed'}")

                # Try npm test
                test_result = subprocess.run(
                    ["npm", "test", "--", "--passWithNoTests"],
                    capture_output=True,
                    text=True,
                    cwd=str(_project_dir),
                    timeout=120
                )
                checks.append(f"Tests: {'✅ Passed' if test_result.returncode == 0 else '❌ Failed'}")

            except Exception:
                checks.append("Basic checks not available")

            return jsonify({
                "success": True,
                "output": f"Quality checks completed:\n" + "\n".join(checks)
            })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Quality check timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================================
# Configuration Helper API
# ===========================================

# Configuration file mappings
CONFIG_ROUTES = {
    "quality gates": {
        "patterns": ["quality", "gates", "lint", "test", "checks", "verification", "qa"],
        "file_path": "/home/vibes/vibes/quality-gate.config.json",
        "description": "Quality gates configuration - controls lint, test, and verification settings"
    },
    "claude settings": {
        "patterns": ["claude", "settings", "config", "anthropic", "api"],
        "file_path": "/home/vibes/vibes/.claude/settings.json",
        "description": "Claude Code settings - API configuration, model preferences, and behavior"
    },
    "mcp servers": {
        "patterns": ["mcp", "servers", "tools", "plugins", "model context protocol"],
        "file_path": "/home/vibes/vibes/.claude/mcp_servers.json",
        "description": "MCP servers configuration - available tools and plugins"
    },
    "git hooks": {
        "patterns": ["git", "hooks", "pre-commit", "post-commit", "automation"],
        "file_path": "/home/vibes/vibes/hooks/",
        "description": "Git hooks directory - automated scripts that run on git events"
    },
    "docker compose": {
        "patterns": ["docker", "compose", "containers", "services", "deployment"],
        "file_path": "/home/vibes/vibes/docker-compose.yml",
        "description": "Docker Compose configuration - service definitions and deployment"
    },
    "package json": {
        "patterns": ["npm", "package", "dependencies", "scripts", "build"],
        "file_path": "/home/vibes/vibes/package.json",
        "description": "Package configuration - dependencies, scripts, and project metadata"
    },
    "eslint config": {
        "patterns": ["eslint", "linting", "code style", "javascript", "typescript"],
        "file_path": "/home/vibes/vibes/.eslintrc.js",
        "description": "ESLint configuration - JavaScript/TypeScript linting rules"
    },
    "prettier config": {
        "patterns": ["prettier", "formatting", "code format", "style"],
        "file_path": "/home/vibes/vibes/.prettierrc",
        "description": "Prettier configuration - automatic code formatting settings"
    },
    "typescript config": {
        "patterns": ["typescript", "tsconfig", "types", "compilation"],
        "file_path": "/home/vibes/vibes/tsconfig.json",
        "description": "TypeScript configuration - compilation settings and type checking"
    },
    "vite config": {
        "patterns": ["vite", "build tool", "frontend build", "development server"],
        "file_path": "/home/vibes/vibes/vite.config.ts",
        "description": "Vite configuration - build tool and development server settings"
    }
}


@app.route('/api/config/route', methods=['POST'])
@requires_auth
def route_config_request():
    """Route a natural language config request to the appropriate file."""
    data = request.json
    query = data.get("query", "").lower()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    # Score each config route based on pattern matching
    best_match = None
    best_score = 0

    for config_name, config_info in CONFIG_ROUTES.items():
        score = 0
        patterns = config_info["patterns"]

        # Count matching patterns
        for pattern in patterns:
            if pattern in query:
                score += 1
                # Bonus for exact matches
                if pattern == query.strip():
                    score += 2

        # Bonus for matching the config name itself
        if config_name.lower() in query:
            score += 3

        if score > best_score:
            best_score = score
            best_match = (config_name, config_info)

    if not best_match or best_score == 0:
        # Fallback - suggest most common config files
        return jsonify({
            "file_path": "/home/vibes/vibes/.claude/settings.json",
            "description": "No specific match found. Try: 'quality gates', 'mcp servers', 'git hooks', 'claude settings'",
            "suggested_change": "Be more specific about what you want to configure"
        })

    config_name, config_info = best_match
    file_path = config_info["file_path"]

    # Check if file exists and adjust path if needed
    if _project_dir:
        relative_path = file_path.replace("/home/vibes/vibes/", "")
        project_file_path = _project_dir / relative_path
        if project_file_path.exists():
            file_path = str(project_file_path)

    # Generate suggested changes based on common requests
    suggested_change = None
    if "add" in query and "mcp" in query:
        suggested_change = 'Add new MCP server: {"name": {"command": "your-command", "args": []}}'
    elif "quality" in query and ("enable" in query or "disable" in query):
        suggested_change = 'Modify "enabled" field or add to "deniedTools" array'
    elif "hook" in query:
        suggested_change = 'Add git hook script or modify existing hook permissions'
    elif "docker" in query:
        suggested_change = 'Modify service definitions or add new services'

    # Determine section if it's a JSON file
    section = None
    if file_path.endswith('.json'):
        if "mcp" in query:
            section = "mcpServers"
        elif "hook" in query:
            section = "hooks"
        elif "tool" in query:
            section = "deniedTools"

    return jsonify({
        "file_path": file_path,
        "section": section,
        "description": config_info["description"],
        "suggested_change": suggested_change
    })


# ===========================================
# Main
# ===========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vibes Frontend Server")
    parser.add_argument("--project", "-p", type=str, default=".",
                        help="Project directory (default: current)")
    parser.add_argument("--projects-root", type=str, default=None,
                        help="Root directory containing all projects (for switching)")
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

    # Get projects root from arg or env
    projects_root = args.projects_root or os.environ.get("VIBES_PROJECTS_ROOT")
    init_app(str(project_dir), projects_root)

    print(f"[vibes-frontend] Starting server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)
