# LA Agenda Alerts - Command Reference Guide

## 🖥️ Quick Start Commands

```bash
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts
```

---

## 🔄 Cron Job Management

### View All Cron Jobs
```bash
crontab -l
```

### Edit Cron Jobs
```bash
crontab -e
```
This opens the cron file in your default editor (usually nano or vim)

### Remove All Cron Jobs
```bash
crontab -r
```
⚠️ **Warning:** This deletes ALL cron jobs. Use with caution!

### Check if Cron Service is Running
```bash
sudo launchctl list | grep cron
```

---

## 🚀 Manual System Control

### Run Agenda Check Now
```bash
export $(grep -v '^#' .env | xargs)
./scripts/run_once.sh
```

### Test Email System
```bash
export $(grep -v '^#' .env | xargs)
python3 scripts/test_email.py
```

### Run Outreach Worker
```bash
export $(grep -v '^#' .env | xargs)
python3 src/outreach_worker.py
```

### Check for Email Replies
```bash
export $(grep -v '^#' .env | xargs)
python3 src/reply_handler.py
```

### Generate Health Report
```bash
export $(grep -v '^#' .env | xargs)
python3 scripts/health_report.py
```

---

## 🌐 Dashboard Commands

### Start Dashboard
```bash
./scripts/serve_dashboard.sh
# Or specify port:
./scripts/serve_dashboard.sh 8080
```

### Stop Dashboard
Find the process and kill it:
```bash
lsof -ti:8080 | xargs kill -9
```

Or:
```bash
ps aux | grep dashboard_server
kill <PID>
```

### View Dashboard Logs
```bash
tail -f logs/dashboard.log
```

---

## 📊 Log Monitoring

### View All Logs
```bash
tail -f logs/*.log
```

### View Specific Log
```bash
# Main agenda check log
tail -f logs/run.log

# Email log
tail -f logs/email.log

# Outreach log
tail -f logs/outreach.log

# Replies log
tail -f logs/replies.log

# Cron log
tail -f logs/cron.log
```

### Search Logs
```bash
# Find errors
grep "ERROR" logs/run.log

# Find sent emails
grep "Sent" logs/email.log

# Find recent activity
grep "2026-02-01" logs/run.log
```

---

## 📁 File Management

### View Data Directory
```bash
ls -la data/
ls -la data/state/
ls -la data/raw/
```

### Edit Subscribers
```bash
nano data/subscribers.json
# or
vim data/subscribers.json
```

### Edit Sources
```bash
nano src/sources.json
```

### View Processed Leads
```bash
cat ~/Downloads/outreach_processed.txt
```

### Clear All Logs
```bash
rm logs/*.log
touch logs/cron.log logs/run.log logs/email.log logs/outreach.log logs/replies.log logs/dashboard.log
```

---

## 🧪 Testing Commands

### Run All Tests
```bash
python3 tests/test_core.py
```

### Check Python Syntax
```bash
python3 -m py_compile src/*.py
```

### Check if Dependencies Installed
```bash
python3 -c "import sys; print(sys.version)"
```

---

## 🔧 Environment & Config

### View Environment Variables
```bash
cat .env
```

### Reload Environment
```bash
export $(grep -v '^#' .env | xargs)
```

### Check API Key
```bash
echo $AGENT_MAIL_API_KEY
```

### Test Network Connectivity
```bash
# Test if you can reach the API
curl -I https://api.agentmail.ai/v1/send

# Test general internet
ping google.com
```

---

## 📧 Email Troubleshooting

### Test SMTP (if using different provider)
```bash
telnet smtp.gmail.com 587
```

### Check DNS Resolution
```bash
nslookup api.agentmail.ai
dig api.agentmail.ai
```

### Check if USC is blocking
```bash
# Try from different network
# USC blocks many external APIs on their WiFi
```

---

## 🔄 Git Commands (for updates)

### Check Status
```bash
git status
```

### Pull Updates
```bash
git pull origin main
```

### Commit Changes
```bash
git add .
git commit -m "Your message"
git push origin main
```

---

## 📊 System Status Check

### Check All Services
```bash
# Check if dashboard is running
curl -s http://localhost:8080/api/stats

# Check disk space
df -h

# Check memory
free -h
```

### View Current Cron
```bash
crontab -l | grep -A2 "LA Agenda"
```

---

## 🎯 Outreach Management

### Add Leads
```bash
# Edit the leads file
nano ~/Downloads/outreach_leads.txt
```

### View Pending Leads
```bash
grep -v "^#" ~/Downloads/outreach_leads.txt | grep -v "^$"
```

### Count Pending Leads
```bash
grep -c "@" ~/Downloads/outreach_leads.txt
```

### Reset Outreach (⚠️ Dangerous)
```bash
# Clear processed list
> ~/Downloads/outreach_processed.txt
```

---

## 💡 Pro Tips

### Create Aliases (add to ~/.zshrc or ~/.bash_profile)
```bash
alias laa='cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts'
alias laa-logs='tail -f /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts/logs/*.log'
alias laa-run='cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts && export $(grep -v "^#" .env | xargs) && ./scripts/run_once.sh'
alias laa-dash='cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts && ./scripts/serve_dashboard.sh'
```

Then reload:
```bash
source ~/.zshrc
```

### Create One-Line Status Check
```bash
echo "=== LA Agenda Alerts Status ===" && echo "Cron Jobs:" && crontab -l | grep -c "la-agenda-alerts" && echo "Log Files:" && ls -1 logs/*.log | wc -l && echo "Pending Leads:" && grep -c "@" ~/Downloads/outreach_leads.txt 2>/dev/null || echo "0"
```

---

## 🆘 Emergency Commands

### Stop Everything
```bash
# Kill dashboard
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Clear stuck cron
crontab -r

# Reset all state (⚠️ DESTRUCTIVE)
rm -rf data/state/*
> ~/Downloads/outreach_processed.txt
```

### Fix Permissions
```bash
chmod +x scripts/*.sh
chmod +x src/*.py
```

---

## 📱 Useful Shortcuts

| Action | Command |
|--------|---------|
| Go to project | `cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts` |
| View logs | `tail -f logs/*.log` |
| Run manual check | `export $(grep -v '^#' .env | xargs) && ./scripts/run_once.sh` |
| Start dashboard | `./scripts/serve_dashboard.sh` |
| View cron | `crontab -l` |
| Edit cron | `crontab -e` |

---

## 📝 Log File Locations

| File | Location | Contains |
|------|----------|----------|
| Run Log | `logs/run.log` | Agenda check results |
| Email Log | `logs/email.log` | Email sending status |
| Outreach Log | `logs/outreach.log` | Lead processing |
| Replies Log | `logs/replies.log` | Email reply handling |
| Dashboard Log | `logs/dashboard.log` | Dashboard server |
| Cron Log | `logs/cron.log` | Cron job output |

---

**Need help?** Check the dashboard at http://localhost:8080 or review docs/ folder.
