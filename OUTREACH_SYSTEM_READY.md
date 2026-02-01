# LA Agenda Alerts - Outreach Automation System

## ✅ SYSTEM IS LIVE!

Your complete outreach automation is now running. Here's everything you need to know:

---

## 🎯 How It Works

### 1. Add Leads (You Do This)
Drop emails into `~/Downloads/outreach_leads.txt`:
```
john@example.com - John Smith, housing activist
sarah@company.com - Sarah Johnson, urban planning consultant  
info@nonprofit.org - LA Community Coalition
```

### 2. Automatic Processing (System Does This)
**Runs at 9am, 12pm, 3pm daily:**
- Reads new leads from file
- Researches person/business online
- Writes personalized email
- Sends via Agent Mail API
- Records in dashboard

### 3. Reply Handling (System Does This)
**Same times (9am, 12pm, 3pm):**
- Checks for email replies
- Handles unsubscribe requests
- Sends follow-ups to interested people
- Logs everything in dashboard

---

## 🖥️ Dashboard

**Start the dashboard:**
```bash
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts
./scripts/serve_dashboard.sh
```

**Then open:** http://localhost:8080

**Shows:**
- 📧 Emails sent count
- 💬 Replies received
- ⏳ Pending leads
- 🤖 System health status
- 📨 Recent email history
- 💬 Reply history
- ⏳ Pending leads list
- 📋 Live logs

**Auto-refreshes every 30 seconds**

---

## 📁 File Locations

| File | Location | Purpose |
|------|----------|---------|
| Leads input | `~/Downloads/outreach_leads.txt` | Add new leads here |
| Processed leads | `~/Downloads/outreach_processed.txt` | Completed leads |
| Dashboard | `http://localhost:8080` | View everything |
| Logs | `logs/outreach.log` | Activity log |
| Sent emails | `data/state/outreach_sent.json` | Email history |

---

## 🔄 Cron Schedule

| Time | Action |
|------|--------|
| 9:00 AM | Process new leads & send emails |
| 9:05 AM | Check for replies |
| 12:00 PM | Process new leads & send emails |
| 12:05 PM | Check for replies |
| 3:00 PM | Process new leads & send emails |
| 3:05 PM | Check for replies |

---

## 🧪 Testing

**Test the outreach system manually:**
```bash
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts
export $(grep -v '^#' .env | xargs)
python3 src/outreach_worker.py
```

**Test reply handler:**
```bash
python3 src/reply_handler.py
```

**Test dashboard:**
```bash
./scripts/serve_dashboard.sh
```

---

## 📧 Email Template

The system generates personalized emails like this:

```
Subject: Quick question about LA government meetings

Hi [Name],

[I noticed your advocacy work in the LA community].

I built a free tool that monitors LA City Council, PLUM Committee, and 
County Board agendas - sending email alerts when new items are posted. 
It saves hours of manually checking government websites.

Given your involvement with [description], I thought this might help 
you track relevant meetings without the hassle.

Check it out: https://maxnguyen.github.io/la-agenda-alerts/

If it's not useful for you, no worries - just reply STOP and I won't 
email again.

Best,
Max
```

---

## 🔧 Maintenance

**View all cron jobs:**
```bash
crontab -l
```

**Remove outreach automation:**
```bash
crontab -e
# Delete the OUTREACH_AUTOMATION section
```

**Restart dashboard:**
```bash
# If port 8080 is in use:
lsof -ti:8080 | xargs kill -9
./scripts/serve_dashboard.sh
```

---

## 📊 Tracking & Logs

Everything is logged:
- **outreach.log** - All outreach activity
- **replies.log** - Reply handling
- **dashboard.log** - Dashboard server
- **run.log** - Main agenda checker

View live in dashboard or:
```bash
tail -f logs/outreach.log
```

---

## ✅ Next Steps

1. **Add your first leads** to `~/Downloads/outreach_leads.txt`
2. **Start the dashboard**: `./scripts/serve_dashboard.sh`
3. **Watch it work** at http://localhost:8080
4. **Deploy website**: Follow DEPLOY_NOW.md to go live

---

## 🎉 Summary

Your LA Agenda Alerts system now has:

✅ **Automated agenda monitoring** (3x daily)  
✅ **Automated outreach** (3x daily)  
✅ **Automated reply handling** (3x daily)  
✅ **Local dashboard** (live web interface)  
✅ **Lead management** (simple text file)  
✅ **Email tracking** (full history)  

**Everything runs automatically. Just add leads and watch it work!**
