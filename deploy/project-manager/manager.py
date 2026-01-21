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
"""

import os
import json
import subprocess
import secrets
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
import docker

app = Flask(__name__)

# Configuration
PROJECTS_BASE = Path(os.environ.get("PROJECTS_BASE", "/home/vibes/projects"))
NETWORK_NAME = os.environ.get("DOCKER_NETWORK", "vibes-network")
BASE_PORT = int(os.environ.get("BASE_PORT", "3010"))
MAX_PROJECTS = int(os.environ.get("MAX_PROJECTS", "10"))
FRONTEND_IMAGE = os.environ.get("FRONTEND_IMAGE", "deploy-frontend:latest")

# Docker client
docker_client = docker.from_env()

# Projects database (file-based for simplicity)
PROJECTS_DB = Path("/data/projects.json")


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

    try:
        container = docker_client.containers.get(container_name(project_id))
        container.start()
        return jsonify({"success": True, "status": "running"})
    except docker.errors.NotFound:
        # Recreate container
        proj = projects[project_id]
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


# ===========================================
# Main
# ===========================================

if __name__ == "__main__":
    port = int(os.environ.get("MANAGER_PORT", "3009"))
    print(f"[project-manager] Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
