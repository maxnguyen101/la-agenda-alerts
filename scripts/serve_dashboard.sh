#!/bin/bash
#
# Start the local dashboard server
# Usage: ./scripts/serve_dashboard.sh [port]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PORT="${1:-8080}"

echo "🚀 Starting LA Agenda Alerts Dashboard..."
echo "📊 Dashboard will be available at: http://localhost:$PORT"
echo ""

# Check if already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port $PORT is already in use!"
    echo "Dashboard may already be running at http://localhost:$PORT"
    exit 1
fi

cd "$PROJECT_DIR"

# Load environment
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Create necessary directories
mkdir -p logs data/state

# Start the server
echo "Starting server... (Press Ctrl+C to stop)"
python3 src/dashboard_server.py $PORT
