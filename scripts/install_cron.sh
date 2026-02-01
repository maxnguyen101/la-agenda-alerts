#!/bin/bash
#
# Install cron jobs for LA Agenda Alerts
# Usage: ./scripts/install_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create temporary crontab
echo "Installing cron jobs for LA Agenda Alerts..."

# Get current crontab (or empty if none)
crontab -l 2>/dev/null > /tmp/current_crontab || true

# Remove existing LA Agenda Alerts entries
grep -v "# LA Agenda Alerts" /tmp/current_crontab > /tmp/new_crontab 2>/dev/null || true

# Add header
cat >> /tmp/new_crontab << EOF
# LA Agenda Alerts - Cron Jobs
# Installed: $(date)

# Run checks 3x daily at 8:00 AM, 1:00 PM, 6:00 PM
0 8,13,18 * * * cd "$PROJECT_DIR" && ./scripts/run_once.sh >> "$PROJECT_DIR/logs/cron.log" 2>&1

# Daily health report at 7:00 AM
0 7 * * * cd "$PROJECT_DIR" && python3 scripts/health_report.py >> "$PROJECT_DIR/logs/cron.log" 2>&1

# LA Agenda Alerts - End
EOF

# Install new crontab
crontab /tmp/new_crontab

# Verify
echo ""
echo "✅ Cron jobs installed!"
echo ""
echo "Current crontab:"
echo "----------------"
crontab -l | grep -A20 "LA Agenda Alerts"
echo ""

# Save proof
crontab -l > "$PROJECT_DIR/docs/CRON_PROOF.txt"
echo "Proof saved to: docs/CRON_PROOF.txt"

# Cleanup
rm -f /tmp/current_crontab /tmp/new_crontab

echo ""
echo "To remove cron jobs, run: crontab -e and delete the LA Agenda Alerts section"
