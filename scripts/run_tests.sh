#!/bin/bash
#
# Run all tests for LA Agenda Alerts
# Usage: ./scripts/run_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Running LA Agenda Alerts Tests..."
echo "================================"

# Run Python tests
python3 tests/test_core.py

echo ""
echo "All tests complete!"
