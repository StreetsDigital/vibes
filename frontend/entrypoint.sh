#!/bin/bash
# Vibes Frontend Entrypoint
# Fixes permissions on mounted volumes and sets up Claude config

# Ensure .claude directory exists
mkdir -p /home/vibes/.claude

# Always update MCP settings from image (ensures latest config)
if [ -f "/app/frontend/claude_settings.json" ]; then
    cp /app/frontend/claude_settings.json /home/vibes/.claude/settings.json
fi

# Fix ownership of .claude directory (mounted volume may have root ownership)
chown -R vibes:vibes /home/vibes/.claude 2>/dev/null || true

# Fix ownership of /projects if writable
if [ -w "/projects" ]; then
    chown -R vibes:vibes /projects 2>/dev/null || true
fi

# Run as root - the server will use runuser for Claude commands
exec "$@"
