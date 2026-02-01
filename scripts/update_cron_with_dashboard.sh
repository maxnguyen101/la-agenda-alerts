#!/bin/bash
#
# Update cron jobs to include dashboard refresh
# Usage: ./scripts/update_cron_with_dashboard.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Updating cron jobs to include dashboard auto-refresh..."

# Get current crontab
crontab -l 2>/dev/null > /tmp/current_crontab.txt || true

# Remove old dashboard refresh entries
grep -v "dashboard_refresh" /tmp/current_crontab.txt > /tmp/clean_crontab.txt 2>/dev/null || true

# Add dashboard refresh every 30 minutes
cat >> /tmp/clean_crontab.txt << EOF

# DASHBOARD_REFRESH - Auto-refresh dashboard data every 30 minutes
*/30 * * * * cd "$PROJECT_DIR" && curl -s http://localhost:8080/api/stats > /dev/null 2>&1 || true
# DASHBOARD_REFRESH - End
EOF

# Install updated crontab
crontab /tmp/clean_crontab.txt

echo "✅ Dashboard refresh added to cron!"
echo ""
echo "Schedule:"
echo "  - Dashboard stats refreshed every 30 minutes"
echo ""
echo "To view: crontab -l"
