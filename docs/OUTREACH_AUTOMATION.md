# LA Agenda Alerts - Outreach Automation System

## Overview
Automated personalized outreach system that researches leads and sends custom emails.

## How It Works

### 1. Adding Leads
Drop emails into `~/Downloads/outreach_leads.txt` (one per line):
```
john@example.com - John Smith, housing activist
sarah@company.com - Sarah Johnson, urban planning firm
info@nonprofit.org - LA Community Coalition
```

### 2. Automatic Processing
Cron runs at **9am, 12pm, 3pm daily**:
- Reads new leads from the file
- Researches each person/business online
- Writes personalized email
- Sends via Agent Mail API
- Moves lead to "processed" list

### 3. Reply Handling
Same cron checks for replies at 9am, 12pm, 3pm:
- Reads incoming emails
- Drafts responses
- Logs all activity

### 4. Dashboard
Local web interface at `http://localhost:8080`:
- View all emails sent
- See bot status & logs
- Track replies
- Monitor system health

## Files

| File | Purpose |
|------|---------|
| `~/Downloads/outreach_leads.txt` | Drop new leads here |
| `~/Downloads/outreach_processed.txt` | Completed leads |
| `src/outreach_worker.py` | Main automation script |
| `src/reply_handler.py` | Handles email replies |
| `web/dashboard.html` | Local dashboard |
| `scripts/serve_dashboard.sh` | Starts dashboard server |

## Dashboard

Start the dashboard:
```bash
./scripts/serve_dashboard.sh
```

Then open: http://localhost:8080

## Logs

All activity logged to:
- `logs/outreach.log` - Outreach activity
- `logs/replies.log` - Reply handling
- `logs/dashboard.log` - Dashboard server

## Manual Run

Test the system manually:
```bash
# Process new leads
python3 src/outreach_worker.py

# Check for replies
python3 src/reply_handler.py

# Start dashboard
python3 src/dashboard_server.py
```
