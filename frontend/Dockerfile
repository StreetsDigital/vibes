# Vibes Frontend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask flask-cors pyyaml sqlalchemy mcp

# Install Claude CLI and Skills tools
RUN apt-get update && apt-get install -y curl git sudo && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @anthropic-ai/claude-code add-skill openskills && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user for Claude CLI (required for --dangerously-skip-permissions)
# Use UID 1000 to match typical host user for volume permissions
RUN useradd -m -s /bin/bash -u 1000 vibes && \
    mkdir -p /home/vibes/.claude && \
    chown -R vibes:vibes /home/vibes

# Copy MCP server config for Claude (context7, etc.)
COPY frontend/claude_settings.json /home/vibes/.claude/settings.json
RUN chown vibes:vibes /home/vibes/.claude/settings.json

# Copy app
COPY frontend/ /app/frontend/
COPY frontend-react/dist/ /app/frontend-react/dist/

# Copy MCP servers for vibecoding features
COPY mcp_server/ /app/mcp_server/

# Set ownership so vibes user can access
RUN chown -R vibes:vibes /app

ENV PYTHONUNBUFFERED=1

EXPOSE 3000

WORKDIR /app/frontend

# Entrypoint script to fix permissions and start server
COPY --chmod=755 frontend/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "server.py", "--project", "/projects", "--port", "3000"]
