#!/bin/bash
#
# Serve the LA Agenda Alerts landing page locally
# Usage: ./scripts/serve_web.sh [port]

PORT=${1:-8080}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR/web"

echo "🚀 Starting LA Agenda Alerts web server..."
echo "📁 Serving from: $PROJECT_DIR/web"
echo "🌐 URL: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Try Python 3 first, fallback to Python
if command -v python3 &> /dev/null; then
    python3 -m http.server $PORT
elif command -v python &> /dev/null; then
    python -m SimpleHTTPServer $PORT
else
    echo "❌ Python not found. Install Python to serve the web page."
    exit 1
fi
