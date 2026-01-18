#!/usr/bin/env bash
#
# Log an event to the dashboard
# ==============================
#
# Usage:
#   log-event.sh <type> <message> [data]
#
# Types: session_start, session_end, feature_complete, quality_check,
#        skill_saved, commit, edit, error
#
# Examples:
#   log-event.sh session_start "Started new coding session"
#   log-event.sh feature_complete "Implemented user auth"
#   log-event.sh quality_check "All checks passed" '{"tests":true,"lint":true}'
#

LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/activity.jsonl"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Get arguments
TYPE="${1:-event}"
MESSAGE="${2:-}"
DATA="${3:-{}}"

# Get timestamp
TIMESTAMP=$(date -Iseconds)

# Get project info if available
PROJECT="${PWD##*/}"
BRANCH=$(git branch --show-current 2>/dev/null || echo "")

# Build JSON entry
JSON=$(cat <<EOF
{"timestamp":"$TIMESTAMP","type":"$TYPE","message":"$MESSAGE","project":"$PROJECT","branch":"$BRANCH","data":$DATA}
EOF
)

# Append to log file
echo "$JSON" >> "$LOG_FILE"

# Also echo for debugging
if [ -n "$VIBECODE_DEBUG" ]; then
    echo "[LOG] $TYPE: $MESSAGE"
fi
