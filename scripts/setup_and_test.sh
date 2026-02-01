#!/bin/bash
#
# Complete setup and test for LA Agenda Alerts
# Usage: ./scripts/setup_and_test.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=============================================="
echo "LA Agenda Alerts - Setup and Test"
echo "=============================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Check environment variables
echo "Checking environment variables..."
if [ -f ".env" ]; then
    source .env
    echo "✅ .env file found"
else
    echo "⚠️  .env file not found - create one with:"
    echo "   AGENT_MAIL_API_KEY=your_key"
    echo "   OPERATOR_EMAIL=youremail@example.com"
    echo "   OPERATOR_IMESSAGE=youremail@example.com"
    exit 1
fi

if [ -n "$AGENT_MAIL_API_KEY" ]; then
    echo "✅ AGENT_MAIL_API_KEY is set"
else
    echo "❌ AGENT_MAIL_API_KEY is not set"
    exit 1
fi

echo ""

# Run tests
echo "Running tests..."
./scripts/run_tests.sh
echo ""

# Run pipeline once
echo "Running pipeline test (fetch only, no email)..."
python3 src/fetch_sources.py 2>&1 | tail -20
echo ""

# Check output
echo "Checking generated files..."
if [ -d "data/raw" ]; then
    RUN_COUNT=$(find data/raw -name "manifest.json" | wc -l)
    echo "✅ Found $RUN_COUNT fetch runs"
else
    echo "⚠️  No fetch runs yet"
fi

if [ -f "data/state/current_items.json" ]; then
    ITEM_COUNT=$(python3 -c "import json; print(len(json.load(open('data/state/current_items.json'))))")
    echo "✅ Found $ITEM_COUNT parsed items"
fi

echo ""
echo "=============================================="
echo "Setup complete!"
echo "=============================================="
echo ""
echo "To complete installation:"
echo "1. Run: ./scripts/install_cron.sh"
echo "2. Test email: ./scripts/run_once.sh"
echo "3. Check logs: tail -f logs/run.log"
echo ""
