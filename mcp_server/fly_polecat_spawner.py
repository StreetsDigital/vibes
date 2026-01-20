"""
Fly.io Polecat Spawner
======================

Spawn ephemeral Claude agents on Fly.io Machines for burst capacity.

Architecture:
  Base Server (Hetzner)     Fly.io Machines
  ├── Mayor (orchestrator)  ├── Polecat-1 (working on feature)
  ├── Kanban UI             ├── Polecat-2 (working on feature)
  ├── Dashboard             └── (auto-shutdown when idle)
  └── Beads (git state)

Benefits:
- Pay only when agents are working (~$0.02/hr per agent)
- Scale to 20+ parallel agents instantly
- Auto-shutdown after task completion
- State persists in Beads (on base server)

Usage:
    spawner = FlyPolecatSpawner(api_token="...", app_name="vibes-polecats")

    # Spawn a Polecat for a Convoy
    polecat = spawner.spawn(convoy, callback_url="https://vibes.domain.com/webhook")

    # Polecat works, updates Beads via webhook
    # Auto-terminates when done
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# ===========================================
# Configuration
# ===========================================

@dataclass
class FlyConfig:
    """Configuration for Fly.io integration."""
    api_token: str
    app_name: str = "vibes-polecats"
    region: str = "iad"  # US East by default
    vm_size: str = "shared-cpu-2x"  # 2 shared vCPUs, 512MB
    vm_memory: int = 1024  # MB
    max_runtime: int = 1800  # 30 minutes max
    idle_timeout: int = 300  # 5 minutes idle = shutdown

    # Image with Claude CLI pre-installed
    image: str = "ghcr.io/anthropics/claude-code:latest"


# ===========================================
# Fly.io API Client
# ===========================================

class FlyAPIClient:
    """Client for Fly.io Machines API."""

    BASE_URL = "https://api.machines.dev/v1"

    def __init__(self, config: FlyConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        """Make an API request."""
        url = f"{self.BASE_URL}/apps/{self.config.app_name}{path}"

        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            json=data,
            timeout=30
        )

        if response.status_code >= 400:
            raise Exception(f"Fly API error: {response.status_code} - {response.text}")

        return response.json() if response.text else {}

    def create_machine(self, name: str, env: dict, cmd: list) -> dict:
        """Create a new Fly Machine."""
        data = {
            "name": name,
            "region": self.config.region,
            "config": {
                "image": self.config.image,
                "env": env,
                "guest": {
                    "cpu_kind": "shared",
                    "cpus": 2,
                    "memory_mb": self.config.vm_memory
                },
                "auto_destroy": True,  # Clean up when stopped
                "restart": {
                    "policy": "no"  # Don't restart on exit
                },
                "services": [],  # No exposed ports needed
                "processes": [
                    {
                        "name": "polecat",
                        "entrypoint": cmd
                    }
                ]
            }
        }

        return self._request("POST", "/machines", data)

    def get_machine(self, machine_id: str) -> dict:
        """Get machine status."""
        return self._request("GET", f"/machines/{machine_id}")

    def stop_machine(self, machine_id: str) -> dict:
        """Stop a machine."""
        return self._request("POST", f"/machines/{machine_id}/stop")

    def destroy_machine(self, machine_id: str) -> dict:
        """Destroy a machine."""
        return self._request("DELETE", f"/machines/{machine_id}")

    def list_machines(self) -> list:
        """List all machines in the app."""
        return self._request("GET", "/machines")


# ===========================================
# Polecat Spawner
# ===========================================

@dataclass
class PolecatInstance:
    """Represents a running Polecat on Fly.io."""
    id: str
    machine_id: str
    convoy_id: str
    status: str  # starting, running, completed, failed
    created_at: str
    region: str
    callback_url: Optional[str] = None


class FlyPolecatSpawner:
    """
    Spawns ephemeral Polecats on Fly.io Machines.

    Each Polecat:
    1. Receives a Convoy (group of Beads) to work on
    2. Clones the project repo
    3. Runs Claude Code to implement features
    4. Reports progress via webhook
    5. Auto-terminates when done
    """

    def __init__(self, config: FlyConfig):
        self.config = config
        self.client = FlyAPIClient(config)
        self._active_polecats: Dict[str, PolecatInstance] = {}

    def spawn(
        self,
        convoy_id: str,
        project_repo: str,
        beads_data: List[dict],
        callback_url: str,
        anthropic_api_key: str,
        branch: str = "main"
    ) -> PolecatInstance:
        """
        Spawn a new Polecat to work on a Convoy.

        Args:
            convoy_id: ID of the Convoy to work on
            project_repo: Git repo URL to clone
            beads_data: List of Bead dicts to work on
            callback_url: Webhook URL for progress updates
            anthropic_api_key: API key for Claude
            branch: Git branch to work on

        Returns:
            PolecatInstance with machine details
        """
        polecat_id = f"polecat-{convoy_id}-{int(time.time())}"

        # Build the task prompt
        task_prompt = self._build_task_prompt(beads_data)

        # Environment variables for the Polecat
        env = {
            "ANTHROPIC_API_KEY": anthropic_api_key,
            "POLECAT_ID": polecat_id,
            "CONVOY_ID": convoy_id,
            "PROJECT_REPO": project_repo,
            "PROJECT_BRANCH": branch,
            "CALLBACK_URL": callback_url,
            "VIBES_USE_BEADS": "true",
            "TASK_PROMPT": task_prompt,
            "MAX_RUNTIME": str(self.config.max_runtime),
        }

        # Command to run
        cmd = [
            "/bin/sh", "-c",
            """
            set -e

            # Clone the project
            git clone --branch $PROJECT_BRANCH --depth 1 $PROJECT_REPO /workspace
            cd /workspace

            # Report starting
            curl -X POST $CALLBACK_URL/polecat/started \
                -H "Content-Type: application/json" \
                -d '{"polecat_id": "'$POLECAT_ID'", "convoy_id": "'$CONVOY_ID'"}'

            # Run Claude Code with the task
            claude --print --dangerously-skip-permissions -p "$TASK_PROMPT" 2>&1 | \
                while IFS= read -r line; do
                    echo "$line"
                    # Send progress updates for key events
                    if echo "$line" | grep -q "FEATURE_COMPLETE\|FEATURE_BLOCKED\|Error"; then
                        curl -X POST $CALLBACK_URL/polecat/progress \
                            -H "Content-Type: application/json" \
                            -d '{"polecat_id": "'$POLECAT_ID'", "message": "'"$line"'"}'
                    fi
                done

            # Push changes if any
            git add -A
            git diff --staged --quiet || git commit -m "Polecat $POLECAT_ID: Convoy $CONVOY_ID"
            git push origin $PROJECT_BRANCH || true

            # Report completion
            curl -X POST $CALLBACK_URL/polecat/completed \
                -H "Content-Type: application/json" \
                -d '{"polecat_id": "'$POLECAT_ID'", "convoy_id": "'$CONVOY_ID'", "status": "completed"}'
            """
        ]

        # Create the machine
        result = self.client.create_machine(
            name=polecat_id,
            env=env,
            cmd=cmd
        )

        instance = PolecatInstance(
            id=polecat_id,
            machine_id=result["id"],
            convoy_id=convoy_id,
            status="starting",
            created_at=datetime.now().isoformat(),
            region=result.get("region", self.config.region),
            callback_url=callback_url
        )

        self._active_polecats[polecat_id] = instance
        return instance

    def _build_task_prompt(self, beads_data: List[dict]) -> str:
        """Build a task prompt from Bead data."""
        lines = [
            "You are a Polecat - an ephemeral worker agent.",
            "Your task is to implement the following features:",
            ""
        ]

        for i, bead in enumerate(beads_data, 1):
            lines.append(f"## Feature {i}: {bead.get('name', 'Unknown')}")
            lines.append(f"Description: {bead.get('description', 'No description')}")

            test_cases = bead.get('test_cases', [])
            if test_cases:
                lines.append("Test cases:")
                for tc in test_cases:
                    lines.append(f"  - {tc}")
            lines.append("")

        lines.extend([
            "## Instructions",
            "1. Implement each feature following existing code patterns",
            "2. Write tests for all test cases",
            "3. Run tests to verify implementation",
            "4. Output FEATURE_COMPLETE when done with each feature",
            "5. Output FEATURE_BLOCKED: <reason> if you cannot proceed",
            "",
            "Begin implementation."
        ])

        return "\n".join(lines)

    def get_status(self, polecat_id: str) -> Optional[PolecatInstance]:
        """Get status of a Polecat."""
        instance = self._active_polecats.get(polecat_id)
        if not instance:
            return None

        # Refresh status from Fly
        try:
            machine = self.client.get_machine(instance.machine_id)
            instance.status = machine.get("state", "unknown")
        except Exception:
            instance.status = "unknown"

        return instance

    def terminate(self, polecat_id: str) -> bool:
        """Terminate a Polecat."""
        instance = self._active_polecats.get(polecat_id)
        if not instance:
            return False

        try:
            self.client.destroy_machine(instance.machine_id)
            del self._active_polecats[polecat_id]
            return True
        except Exception:
            return False

    def list_active(self) -> List[PolecatInstance]:
        """List all active Polecats."""
        # Refresh statuses
        for polecat_id in list(self._active_polecats.keys()):
            self.get_status(polecat_id)

        return list(self._active_polecats.values())

    def cleanup_completed(self) -> int:
        """Clean up completed/failed Polecats."""
        cleaned = 0
        for polecat_id, instance in list(self._active_polecats.items()):
            if instance.status in ["stopped", "destroyed", "failed"]:
                try:
                    self.client.destroy_machine(instance.machine_id)
                except Exception:
                    pass
                del self._active_polecats[polecat_id]
                cleaned += 1

        return cleaned


# ===========================================
# Webhook Handler (for Mayor to receive updates)
# ===========================================

class PolecatWebhookHandler:
    """
    Handles webhook callbacks from Polecats.

    Integrate with your web framework (Flask, FastAPI, etc.)
    """

    def __init__(self, mayor: "Mayor", bead_store: "BeadStore"):
        self.mayor = mayor
        self.bead_store = bead_store
        self._events: List[dict] = []

    def handle_started(self, data: dict) -> dict:
        """Handle Polecat started event."""
        event = {
            "type": "polecat_started",
            "polecat_id": data.get("polecat_id"),
            "convoy_id": data.get("convoy_id"),
            "timestamp": datetime.now().isoformat()
        }
        self._events.append(event)

        return {"status": "ok"}

    def handle_progress(self, data: dict) -> dict:
        """Handle Polecat progress event."""
        message = data.get("message", "")
        polecat_id = data.get("polecat_id")

        event = {
            "type": "polecat_progress",
            "polecat_id": polecat_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self._events.append(event)

        # Check for completion markers
        if "FEATURE_COMPLETE" in message:
            # Could update Bead status here
            pass
        elif "FEATURE_BLOCKED" in message:
            # Could mark Bead as needs_review
            pass

        return {"status": "ok"}

    def handle_completed(self, data: dict) -> dict:
        """Handle Polecat completed event."""
        polecat_id = data.get("polecat_id")
        convoy_id = data.get("convoy_id")
        status = data.get("status", "completed")

        event = {
            "type": "polecat_completed",
            "polecat_id": polecat_id,
            "convoy_id": convoy_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        self._events.append(event)

        # Pull latest changes and refresh Beads
        # (In production, trigger a git pull on the base server)

        return {"status": "ok", "next_action": "refresh_beads"}

    def get_recent_events(self, limit: int = 50) -> List[dict]:
        """Get recent events."""
        return self._events[-limit:]


# ===========================================
# Integration with Mayor
# ===========================================

def create_fly_spawner_from_env() -> Optional[FlyPolecatSpawner]:
    """Create a Fly spawner from environment variables."""
    api_token = os.getenv("FLY_API_TOKEN")

    if not api_token:
        return None

    config = FlyConfig(
        api_token=api_token,
        app_name=os.getenv("FLY_APP_NAME", "vibes-polecats"),
        region=os.getenv("FLY_REGION", "iad"),
    )

    return FlyPolecatSpawner(config)


# ===========================================
# CLI for testing
# ===========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fly.io Polecat Spawner")
    parser.add_argument("--list", action="store_true", help="List active Polecats")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup completed Polecats")

    args = parser.parse_args()

    spawner = create_fly_spawner_from_env()

    if not spawner:
        print("Error: FLY_API_TOKEN not set")
        exit(1)

    if args.list:
        polecats = spawner.list_active()
        for p in polecats:
            print(f"{p.id}: {p.status} (convoy: {p.convoy_id})")

    elif args.cleanup:
        cleaned = spawner.cleanup_completed()
        print(f"Cleaned up {cleaned} Polecats")
