#!/bin/bash
#
# Install outreach automation cron jobs
# Usage: ./scripts/install_outreach_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Installing outreach automation cron jobs..."

# Get current crontab
crontab -l 2>/dev/null > /tmp/current_crontab.txt || true

# Remove old outreach jobs
grep -v "OUTREACH_AUTOMATION" /tmp/current_crontab.txt > /tmp/clean_crontab.txt 2>/dev/null || true

# Add new outreach cron jobs
cat >> /tmp/clean_crontab.txt << EOF

# OUTREACH_AUTOMATION - LA Agenda Alerts Outreach
# Run outreach worker at 9am, 12pm, 3pm
0 9,12,15 * * * cd "$PROJECT_DIR" && export \$(grep -v '^#' .env | xargs) && python3 src/outreach_worker.py >> "$PROJECT_DIR/logs/outreach.log" 2>&1

# Check for email replies at 9am, 12pm, 3pm
5 9,12,15 * * * cd "$PROJECT_DIR" && export \$(grep -v '^#' .env | xargs) && python3 src/reply_handler.py >> "$PROJECT_DIR/logs/replies.log" 2>&1

# OUTREACH_AUTOMATION - End
EOF

# Install new crontab
crontab /tmp/clean_crontab.txt

echo "✅ Outreach automation cron jobs installed!"
echo ""
echo "Schedule:"
echo "  - 9:00 AM: Check for new leads & send emails"
echo "  - 12:00 PM: Check for new leads & send emails"
echo "  - 3:00 PM: Check for new leads & send emails"
echo "  - Replies checked 5 minutes after each send"
echo ""
echo "To view: crontab -l"
echo "To remove: crontab -e and delete OUTREACH_AUTOMATION section"
