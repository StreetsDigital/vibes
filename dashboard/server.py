#!/usr/bin/env python3
"""
Vibecode Dashboard Server
=========================
Simple web server to view logs and activity.

Usage:
    python3 dashboard/server.py [port]

Default port: 8080
Access: http://localhost:8080
"""

import http.server
import socketserver
import json
import os
from pathlib import Path
from datetime import datetime
import urllib.parse

PORT = int(os.environ.get("DASHBOARD_PORT", 8080))
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_FILE = LOG_DIR / "activity.jsonl"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logs(limit=100, event_type=None):
    """Read logs from JSONL file."""
    logs = []
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if event_type and entry.get("type") != event_type:
                        continue
                    logs.append(entry)
                except json.JSONDecodeError:
                    continue
    # Return most recent first
    return list(reversed(logs[-limit:]))


def get_stats():
    """Get summary statistics."""
    logs = get_logs(limit=1000)
    stats = {
        "total_events": len(logs),
        "features_completed": sum(1 for l in logs if l.get("type") == "feature_complete"),
        "quality_checks": sum(1 for l in logs if l.get("type") == "quality_check"),
        "skills_learned": sum(1 for l in logs if l.get("type") == "skill_saved"),
        "commits": sum(1 for l in logs if l.get("type") == "commit"),
        "sessions": sum(1 for l in logs if l.get("type") == "session_start"),
    }
    return stats


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.serve_dashboard()
        elif parsed.path == "/api/logs":
            self.serve_logs()
        elif parsed.path == "/api/stats":
            self.serve_stats()
        elif parsed.path == "/api/skills":
            self.serve_skills()
        else:
            super().do_GET()

    def serve_dashboard(self):
        html = get_dashboard_html()
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_logs(self):
        logs = get_logs(limit=200)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(logs).encode())

    def serve_stats(self):
        stats = get_stats()
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(stats).encode())

    def serve_skills(self):
        skills_dir = Path.home() / ".claude" / "skills" / "learned"
        skills = []
        if skills_dir.exists():
            for f in skills_dir.glob("*.md"):
                content = f.read_text()
                # Parse YAML frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import re
                        name = re.search(r"name:\s*(.+)", parts[1])
                        desc = re.search(r"description:\s*(.+)", parts[1])
                        skills.append({
                            "file": f.name,
                            "name": name.group(1) if name else f.stem,
                            "description": desc.group(1) if desc else "",
                        })
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(skills).encode())

    def log_message(self, format, *args):
        # Suppress access logs
        pass


def get_dashboard_html():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vibecode Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            background: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 16px 20px;
            margin-bottom: 20px;
        }
        header h1 { color: #58a6ff; font-size: 1.5em; }
        header .subtitle { color: #8b949e; font-size: 0.9em; }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #58a6ff;
        }
        .stat-card .label { color: #8b949e; font-size: 0.85em; }

        .section {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .section-header {
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .section-body { padding: 16px; max-height: 500px; overflow-y: auto; }

        .log-entry {
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 8px;
            background: #0d1117;
            border-left: 3px solid #30363d;
            font-size: 0.9em;
        }
        .log-entry.feature_complete { border-left-color: #3fb950; }
        .log-entry.quality_check { border-left-color: #58a6ff; }
        .log-entry.skill_saved { border-left-color: #a371f7; }
        .log-entry.commit { border-left-color: #f0883e; }
        .log-entry.session_start { border-left-color: #8b949e; }
        .log-entry.error { border-left-color: #f85149; }

        .log-time { color: #8b949e; font-size: 0.8em; }
        .log-type {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-right: 8px;
            background: #30363d;
        }
        .log-message { margin-top: 4px; }

        .skill-item {
            padding: 12px;
            background: #0d1117;
            border-radius: 4px;
            margin-bottom: 8px;
        }
        .skill-name { color: #a371f7; font-weight: 600; }
        .skill-desc { color: #8b949e; font-size: 0.9em; margin-top: 4px; }

        .refresh-btn {
            background: #238636;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
        }
        .refresh-btn:hover { background: #2ea043; }

        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #8b949e;
            font-size: 0.85em;
        }

        .empty { color: #8b949e; text-align: center; padding: 40px; }

        @media (max-width: 600px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            .stat-card .value { font-size: 1.5em; }
        }
    </style>
</head>
<body>
    <header>
        <h1>Vibecode Dashboard</h1>
        <div class="subtitle">Real-time activity monitoring</div>
    </header>

    <div class="container">
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="value" id="stat-sessions">-</div>
                <div class="label">Sessions</div>
            </div>
            <div class="stat-card">
                <div class="value" id="stat-features">-</div>
                <div class="label">Features</div>
            </div>
            <div class="stat-card">
                <div class="value" id="stat-quality">-</div>
                <div class="label">Quality Checks</div>
            </div>
            <div class="stat-card">
                <div class="value" id="stat-skills">-</div>
                <div class="label">Skills Learned</div>
            </div>
            <div class="stat-card">
                <div class="value" id="stat-commits">-</div>
                <div class="label">Commits</div>
            </div>
            <div class="stat-card">
                <div class="value" id="stat-total">-</div>
                <div class="label">Total Events</div>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <span>Activity Log</span>
                <div class="auto-refresh">
                    <input type="checkbox" id="auto-refresh" checked>
                    <label for="auto-refresh">Auto-refresh (5s)</label>
                    <button class="refresh-btn" onclick="refresh()">Refresh</button>
                </div>
            </div>
            <div class="section-body" id="logs">
                <div class="empty">Loading...</div>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <span>Learned Skills</span>
            </div>
            <div class="section-body" id="skills">
                <div class="empty">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const stats = await res.json();
                document.getElementById('stat-sessions').textContent = stats.sessions || 0;
                document.getElementById('stat-features').textContent = stats.features_completed || 0;
                document.getElementById('stat-quality').textContent = stats.quality_checks || 0;
                document.getElementById('stat-skills').textContent = stats.skills_learned || 0;
                document.getElementById('stat-commits').textContent = stats.commits || 0;
                document.getElementById('stat-total').textContent = stats.total_events || 0;
            } catch (e) {
                console.error('Failed to fetch stats:', e);
            }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const logs = await res.json();
                const container = document.getElementById('logs');

                if (logs.length === 0) {
                    container.innerHTML = '<div class="empty">No activity yet. Start coding!</div>';
                    return;
                }

                container.innerHTML = logs.map(log => `
                    <div class="log-entry ${log.type || ''}">
                        <div>
                            <span class="log-type">${log.type || 'event'}</span>
                            <span class="log-time">${formatTime(log.timestamp)}</span>
                        </div>
                        <div class="log-message">${escapeHtml(log.message || JSON.stringify(log.data || {}))}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Failed to fetch logs:', e);
            }
        }

        async function fetchSkills() {
            try {
                const res = await fetch('/api/skills');
                const skills = await res.json();
                const container = document.getElementById('skills');

                if (skills.length === 0) {
                    container.innerHTML = '<div class="empty">No skills learned yet. Run /retrospective after debugging!</div>';
                    return;
                }

                container.innerHTML = skills.map(skill => `
                    <div class="skill-item">
                        <div class="skill-name">${escapeHtml(skill.name)}</div>
                        <div class="skill-desc">${escapeHtml(skill.description)}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Failed to fetch skills:', e);
            }
        }

        function formatTime(ts) {
            if (!ts) return '';
            const d = new Date(ts);
            return d.toLocaleString();
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;')
                      .replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;');
        }

        function refresh() {
            fetchStats();
            fetchLogs();
            fetchSkills();
        }

        // Initial load
        refresh();

        // Auto-refresh
        setInterval(() => {
            if (document.getElementById('auto-refresh').checked) {
                refresh();
            }
        }, 5000);
    </script>
</body>
</html>'''


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        PORT = int(sys.argv[1])

    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"")
        print(f"╔══════════════════════════════════════════════════════════════╗")
        print(f"║           VIBECODE DASHBOARD                                 ║")
        print(f"╚══════════════════════════════════════════════════════════════╝")
        print(f"")
        print(f"  Server running at: http://localhost:{PORT}")
        print(f"  Log file: {LOG_FILE}")
        print(f"")
        print(f"  Press Ctrl+C to stop")
        print(f"")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
