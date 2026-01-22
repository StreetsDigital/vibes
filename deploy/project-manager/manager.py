#!/usr/bin/env python3
"""
Project Manager Service
=======================
Manages isolated Docker containers for each vibes project.

API:
  GET  /projects           - List all projects
  POST /projects           - Create new project
  GET  /projects/:id       - Get project status
  DELETE /projects/:id     - Delete project
  POST /projects/:id/start - Start project container
  POST /projects/:id/stop  - Stop project container
  POST /projects/:id/activity - Update last activity (heartbeat)
  GET  /health/system      - System health metrics

Features:
  - Auto-sleep: Projects idle for 30 minutes are automatically stopped
"""

import os
import json
import subprocess
import secrets
import psutil
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, Response
import docker
import requests as http_requests

app = Flask(__name__)

# Configuration
PROJECTS_BASE = Path(os.environ.get("PROJECTS_BASE", "/home/vibes/projects"))
NETWORK_NAME = os.environ.get("DOCKER_NETWORK", "vibes-network")
BASE_PORT = int(os.environ.get("BASE_PORT", "3010"))
MAX_PROJECTS = int(os.environ.get("MAX_PROJECTS", "10"))
FRONTEND_IMAGE = os.environ.get("FRONTEND_IMAGE", "deploy-frontend:latest")
IDLE_TIMEOUT_MINUTES = int(os.environ.get("IDLE_TIMEOUT_MINUTES", "30"))

# Docker client
docker_client = docker.from_env()

# Projects database (file-based for simplicity)
PROJECTS_DB = Path("/data/projects.json")

# Activity tracking (in-memory, persisted to projects.json)
# Format: {project_id: datetime}
_activity_lock = threading.Lock()


def update_activity(project_id: str):
    """Update last activity timestamp for a project."""
    projects = load_projects()
    if project_id in projects:
        projects[project_id]["last_activity"] = datetime.now().isoformat()
        save_projects(projects)


def get_idle_minutes(project: dict) -> int:
    """Get minutes since last activity."""
    last_activity = project.get("last_activity")
    if not last_activity:
        # Use created_at if no activity recorded
        last_activity = project.get("created_at")
    if not last_activity:
        return 0
    try:
        last_dt = datetime.fromisoformat(last_activity)
        delta = datetime.now() - last_dt
        return int(delta.total_seconds() / 60)
    except:
        return 0


def check_idle_projects():
    """Check for idle projects and stop them."""
    projects = load_projects()
    for pid, proj in projects.items():
        # Only check running containers
        status = get_container_status(pid)
        if status != "running":
            continue

        idle_mins = get_idle_minutes(proj)
        if idle_mins >= IDLE_TIMEOUT_MINUTES:
            print(f"[idle-monitor] Stopping idle project {pid} ({proj.get('name')}) - idle for {idle_mins} minutes")
            try:
                container = docker_client.containers.get(container_name(pid))
                container.stop()
                # Record that it was auto-stopped
                projects[pid]["auto_stopped"] = datetime.now().isoformat()
                projects[pid]["auto_stopped_reason"] = f"Idle for {idle_mins} minutes"
                save_projects(projects)
            except Exception as e:
                print(f"[idle-monitor] Error stopping {pid}: {e}")


def idle_monitor_loop():
    """Background thread that checks for idle projects every minute."""
    print(f"[idle-monitor] Started - timeout: {IDLE_TIMEOUT_MINUTES} minutes")
    while True:
        time.sleep(60)  # Check every minute
        try:
            check_idle_projects()
        except Exception as e:
            print(f"[idle-monitor] Error: {e}")


def load_projects() -> dict:
    """Load projects from database file."""
    if PROJECTS_DB.exists():
        return json.loads(PROJECTS_DB.read_text())
    return {}


def save_projects(projects: dict):
    """Save projects to database file."""
    PROJECTS_DB.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_DB.write_text(json.dumps(projects, indent=2))


def get_next_port() -> int:
    """Get next available port for a project."""
    projects = load_projects()
    used_ports = {p.get("port") for p in projects.values()}
    for port in range(BASE_PORT, BASE_PORT + MAX_PROJECTS):
        if port not in used_ports:
            return port
    raise RuntimeError("No available ports")


def container_name(project_id: str) -> str:
    """Get container name for a project."""
    return f"vibes-project-{project_id}"


def get_container_status(project_id: str) -> str:
    """Get status of a project's container."""
    try:
        container = docker_client.containers.get(container_name(project_id))
        return container.status
    except docker.errors.NotFound:
        return "not_created"
    except Exception as e:
        return f"error: {e}"


# ===========================================
# API Routes
# ===========================================

@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/projects", methods=["GET"])
def list_projects():
    """List all projects with their status."""
    projects = load_projects()
    result = []
    for pid, proj in projects.items():
        proj["id"] = pid
        proj["container_status"] = get_container_status(pid)
        proj["idle_minutes"] = get_idle_minutes(proj)
        proj["idle_timeout_minutes"] = IDLE_TIMEOUT_MINUTES
        result.append(proj)
    return jsonify({"projects": result})


@app.route("/projects", methods=["POST"])
def create_project():
    """Create a new project."""
    data = request.json or {}
    name = data.get("name", "").strip()
    git_url = data.get("git_url", "").strip()

    if not name:
        return jsonify({"error": "Project name required"}), 400

    # Check max projects
    projects = load_projects()
    if len(projects) >= MAX_PROJECTS:
        return jsonify({"error": f"Maximum {MAX_PROJECTS} projects allowed"}), 400

    # Generate project ID
    project_id = secrets.token_hex(4)
    project_dir = PROJECTS_BASE / project_id

    try:
        # Create project directory
        project_dir.mkdir(parents=True, exist_ok=True)

        # Clone repo or init empty
        if git_url:
            subprocess.run(
                ["git", "clone", git_url, str(project_dir)],
                check=True, capture_output=True
            )
        else:
            subprocess.run(
                ["git", "init"],
                cwd=str(project_dir),
                check=True, capture_output=True
            )
            # Create basic structure
            (project_dir / ".git" / "beads").mkdir(parents=True, exist_ok=True)

        # Assign port
        port = get_next_port()

        # Save project info
        projects[project_id] = {
            "name": name,
            "git_url": git_url,
            "port": port,
            "created_at": datetime.now().isoformat(),
            "path": str(project_dir),
        }
        save_projects(projects)

        # Create and start container
        _create_container(project_id, port, project_dir)

        return jsonify({
            "success": True,
            "project": {
                "id": project_id,
                "name": name,
                "port": port,
                "url": f"/project/{project_id}/",
            }
        })

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Git error: {e.stderr.decode()}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _create_container(project_id: str, port: int, project_dir: Path):
    """Create and start a project container."""
    name = container_name(project_id)

    # Remove existing container if any
    try:
        old = docker_client.containers.get(name)
        old.remove(force=True)
    except docker.errors.NotFound:
        pass

    # Create new container
    container = docker_client.containers.run(
        FRONTEND_IMAGE,
        name=name,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
        environment={
            "VIBES_USE_BEADS": "true",
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        },
        volumes={
            str(project_dir): {"bind": "/projects", "mode": "rw"},
            "deploy_claude_credentials": {"bind": "/root/.claude", "mode": "rw"},
        },
        network=NETWORK_NAME,
        labels={
            "vibes.project": project_id,
            "vibes.port": str(port),
        },
    )
    return container


@app.route("/projects/<project_id>", methods=["GET"])
def get_project(project_id: str):
    """Get project details."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    proj = projects[project_id]
    proj["id"] = project_id
    proj["container_status"] = get_container_status(project_id)
    return jsonify(proj)


@app.route("/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id: str):
    """Delete a project and its container."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    # Stop and remove container
    try:
        container = docker_client.containers.get(container_name(project_id))
        container.remove(force=True)
    except docker.errors.NotFound:
        pass

    # Remove from database
    project_dir = projects[project_id].get("path")
    del projects[project_id]
    save_projects(projects)

    # Optionally remove project files (commented for safety)
    # if project_dir and Path(project_dir).exists():
    #     shutil.rmtree(project_dir)

    return jsonify({"success": True})


@app.route("/projects/<project_id>/start", methods=["POST"])
def start_project(project_id: str):
    """Start a project's container."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    # Clear auto-stopped flag and update activity
    proj = projects[project_id]
    proj.pop("auto_stopped", None)
    proj.pop("auto_stopped_reason", None)
    proj["last_activity"] = datetime.now().isoformat()
    save_projects(projects)

    try:
        container = docker_client.containers.get(container_name(project_id))
        container.start()
        return jsonify({"success": True, "status": "running"})
    except docker.errors.NotFound:
        # Recreate container
        _create_container(project_id, proj["port"], Path(proj["path"]))
        return jsonify({"success": True, "status": "created"})


@app.route("/projects/<project_id>/stop", methods=["POST"])
def stop_project(project_id: str):
    """Stop a project's container."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    try:
        container = docker_client.containers.get(container_name(project_id))
        container.stop()
        return jsonify({"success": True, "status": "stopped"})
    except docker.errors.NotFound:
        return jsonify({"success": True, "status": "not_running"})


@app.route("/projects/<project_id>/activity", methods=["POST"])
def record_activity(project_id: str):
    """Record activity heartbeat for a project (resets idle timer)."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    # Update activity timestamp
    update_activity(project_id)

    # If container was auto-stopped, restart it
    status = get_container_status(project_id)
    proj = projects[project_id]
    was_auto_stopped = proj.get("auto_stopped")

    if status != "running" and was_auto_stopped:
        # Clear auto-stopped flag and restart
        proj.pop("auto_stopped", None)
        proj.pop("auto_stopped_reason", None)
        save_projects(projects)
        try:
            container = docker_client.containers.get(container_name(project_id))
            container.start()
            return jsonify({
                "success": True,
                "status": "restarted",
                "message": "Project was idle-stopped, now restarted"
            })
        except docker.errors.NotFound:
            _create_container(project_id, proj["port"], Path(proj["path"]))
            return jsonify({
                "success": True,
                "status": "recreated",
                "message": "Project container recreated"
            })

    return jsonify({
        "success": True,
        "status": status,
        "idle_minutes": get_idle_minutes(proj),
        "timeout_minutes": IDLE_TIMEOUT_MINUTES
    })


# ===========================================
# Project Proxy
# ===========================================

@app.route("/project/<project_id>/", defaults={"path": ""})
@app.route("/project/<project_id>/<path:path>")
def proxy_project(project_id: str, path: str):
    """Proxy requests to project containers."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    # Record activity
    update_activity(project_id)

    # Get container status, start if needed
    status = get_container_status(project_id)
    if status != "running":
        proj = projects[project_id]
        try:
            container = docker_client.containers.get(container_name(project_id))
            container.start()
            # Wait a moment for container to be ready
            time.sleep(1)
        except docker.errors.NotFound:
            _create_container(project_id, proj["port"], Path(proj["path"]))
            time.sleep(2)

    # Proxy the request to the container
    container_url = f"http://{container_name(project_id)}:3000/{path}"

    try:
        # Forward the request
        resp = http_requests.request(
            method=request.method,
            url=container_url,
            headers={k: v for k, v in request.headers if k.lower() != "host"},
            data=request.get_data(),
            params=request.args,
            allow_redirects=False,
            timeout=30,
        )

        # Build response
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to project: {str(e)}"}), 502


# ===========================================
# System Health API
# ===========================================

@app.route("/health/system", methods=["GET"])
def system_health():
    """Get system health metrics."""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()

        # Memory
        mem = psutil.virtual_memory()
        mem_total_gb = mem.total / (1024**3)
        mem_used_gb = mem.used / (1024**3)
        mem_percent = mem.percent

        # Disk
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024**3)
        disk_used_gb = disk.used / (1024**3)
        disk_percent = disk.percent

        # Docker containers
        containers = docker_client.containers.list(all=True)
        vibes_containers = [c for c in containers if c.name.startswith('vibes-')]
        running_containers = [c for c in vibes_containers if c.status == 'running']

        # Container details
        container_list = []
        for c in vibes_containers:
            try:
                image_name = c.image.tags[0] if c.image.tags else "unknown"
            except Exception:
                image_name = "unknown"
            container_list.append({
                "name": c.name,
                "status": c.status,
                "image": image_name,
            })

        # Load average (Unix only)
        try:
            load_avg = os.getloadavg()
            load_1m, load_5m, load_15m = load_avg
        except (OSError, AttributeError):
            load_1m = load_5m = load_15m = 0.0

        # Determine health status
        status = "healthy"
        warnings = []

        if cpu_percent > 80:
            status = "warning"
            warnings.append(f"High CPU usage: {cpu_percent}%")
        if mem_percent > 85:
            status = "warning"
            warnings.append(f"High memory usage: {mem_percent}%")
        if disk_percent > 90:
            status = "critical"
            warnings.append(f"Low disk space: {disk_percent}% used")
        if mem_percent > 95:
            status = "critical"
            warnings.append(f"Critical memory usage: {mem_percent}%")

        return jsonify({
            "status": status,
            "warnings": warnings,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "cores": cpu_count,
                "load_1m": round(load_1m, 2),
                "load_5m": round(load_5m, 2),
                "load_15m": round(load_15m, 2),
            },
            "memory": {
                "total_gb": round(mem_total_gb, 1),
                "used_gb": round(mem_used_gb, 1),
                "percent": round(mem_percent, 1),
            },
            "disk": {
                "total_gb": round(disk_total_gb, 1),
                "used_gb": round(disk_used_gb, 1),
                "percent": round(disk_percent, 1),
            },
            "containers": {
                "total": len(vibes_containers),
                "running": len(running_containers),
                "list": container_list,
            },
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ===========================================
# Main
# ===========================================

if __name__ == "__main__":
    port = int(os.environ.get("MANAGER_PORT", "3009"))
    print(f"[project-manager] Starting on port {port}")

    # Start idle monitor background thread
    idle_thread = threading.Thread(target=idle_monitor_loop, daemon=True)
    idle_thread.start()

    app.run(host="0.0.0.0", port=port, debug=False)  # debug=False for threading
