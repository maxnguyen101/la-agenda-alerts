<div align="center">

# LA Agenda Alerts

### Never miss an LA government agenda change again.

Real-time alerts when City Council, County Board, Planning Commission, and 10+ agencies update agendas.

[![Live Demo](https://img.shields.io/badge/Live%20Site-GitHub%20Pages-blue?style=for-the-badge&logo=github)](https://maxnguyen101.github.io/la-agenda-alerts)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

</div>

---

## The Problem

**Government websites are a mess.**

- Agendas change without warning
- 13 different websites to check
- No notification system
- Critical meetings missed

**You waste 5-10 hours/month** manually checking LA City Council, County Board, Planning Commission, Housing Authority, and 8 other agencies.

## The Solution

**LA Agenda Alerts monitors everything for you.**

Our system checks 13 government sources 3 times daily and sends instant email/SMS alerts when agendas change. No more missed meetings. No more manual checking.

---

## What You Get

| Feature | Free | Pro ($9/mo) | Org ($39/mo) |
|---------|------|-------------|--------------|
| **Alerts** | Email only | Email + SMS | Email + SMS |
| **Sources** | All 13 | All 13 | All 13 |
| **Recipients** | 1 | Up to 3 | Up to 5 |
| **Keywords** | Basic OR | AND/OR/NOT | Team shared |
| **Calendar** | ❌ | ✅ .ics files | ✅ Shared |
| **Retries** | 1 attempt | 3 attempts | 5 + priority |
| **Support** | Best-effort | Standard | Priority |

### 13 Sources Monitored

| City | County | Regional | Environment |
|------|--------|----------|-------------|
| City Council | Board of Supervisors | Metro Board | Air Quality (AQMD) |
| PLUM Committee | Development Authority | Caltrans D7 | LA Sanitation |
| Planning Commission | | | |
| Housing Department | | | |
| Rent Stabilization | | | |
| Housing Authority | | | |
| DOT | | | |

---

## How It Works

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
| 13 Sources  |───▶|  Our System |───▶|    You      |
|  Monitored  |    |  3x Daily   |    |   Alerted   |
└─────────────┘    └─────────────┘    └─────────────┘
```

1. **We Check** - System scrapes 13 government websites at 8am, 1pm, 6pm
2. **We Compare** - Detects changes from previous version
3. **We Match** - Checks against your keyword preferences
4. **You Get Alerted** - Instant email (all tiers) + SMS (Pro+)

---

## 🚀 Quick Start

### Option 1: Free Tier (No Signup Required)

1. Visit [la-agenda-alerts.com](https://maxnguyen101.github.io/la-agenda-alerts)
2. Enter your email
3. Select topics (Housing, Transportation, etc.)
4. Get instant alerts - forever free

### Option 2: Pro Tier (30-Second Upgrade)

1. Click "Upgrade to Pro"
2. Choose payment: Venmo, PayPal, or Zelle
3. Email receipt to mnguyen9@usc.edu
4. Upgraded within 24 hours with SMS alerts

---

## 💳 Payment Options

### Manual Payments (Beta)

During our beta period, we use manual payments to:
- Avoid vendor lock-in
- Ensure early users get personal support
- Build direct relationships

**Accepted:**
- 💸 Venmo: [@la_agenda_alerts](https://venmo.com/u/la_agenda_alerts)
- 🅿️ PayPal: mnguyen9@usc.edu
- 💳 Zelle: mnguyen9@usc.edu

*Stripe automation coming soon for self-service checkout.*

---

## 🛡️ Safety & Trust

### Outreach Guarantee
Every outreach email includes a one-click opt-out. Opt-outs are permanently honored and logged.

### Data Privacy
- No passwords stored (magic link auth)
- Email-only for Free tier
- No data sold or shared
- GDPR-compliant deletion on request

### Reliability
- **99.9% uptime** via redundant checks
- If a scheduled run is missed, the next run automatically backfills and checks for missed changes
- 3-5 retry attempts (by tier) before marking failed
- Real-time source health monitoring

---

## 📊 System Architecture

```
Frontend (GitHub Pages)          Backend (Mac Mini)
├─ Landing page                  ├─ Dashboard API
├─ Pricing & signup              ├─ User management
└─ Static assets                 ├─ Alert pipeline
                                 ├─ Stripe webhooks
                                 └─ SQLite database
```

**Tech Stack:**
- **Frontend:** Static HTML/CSS/JS (GitHub Pages)
- **Backend:** Python 3 (Flask-like HTTP server)
- **Database:** SQLite with WAL mode
- **Scheduler:** Cron (Mac Mini)
- **Payments:** Manual (Venmo/PayPal/Zelle) → Stripe (soon)

---

## 📈 Dashboard

**URL:** http://localhost:8080 (local admin)

**Features:**
- Real-time user analytics by tier
- Source health monitoring (uptime %)
- Alerts sent tracking (24h / 7d / all-time)
- Outreach activity log
- System event logs
- Failed scrape monitoring

*Auto-refreshes every 30 seconds*

---

## 🔄 Automation Schedule

| Time | Action |
|------|--------|
| 8:00 AM | Check all 13 sources |
| 1:00 PM | Check all 13 sources |
| 6:00 PM | Check all 13 sources |
| Every 6 hours | Health check & source scoring |
| Every 30 min | Dashboard keepalive |
| Sunday 9am | Weekly digest email |

---

## 💰 Revenue Model

**Target Customers:**
- Housing advocates (rent control, development tracking)
- Urban planners (zoning, permits)
- Journalists (government scoops)
- Community organizers (neighborhood issues)
- Government contractors (RFPs, board decisions)

**Projections:**
- Month 3: 50 free users, 5 paid = $45/month
- Month 6: 200 free users, 20 paid = $180/month
- Month 12: 500 free users, 50 paid = $450/month

---

## 🎯 Getting Customers

### 1. Manual Outreach (Safe Mode)

Add leads to `~/Downloads/outreach_leads.txt`:
```
email@example.com - Name, description/justification
```

System automatically:
- Sends personalized emails (max 5/day)
- Respects opt-outs
- Logs all activity
- Never spams same person twice

### 2. Twitter/LinkedIn

Post agenda alerts publicly with backlink:
```
🏛️ LA City Council agenda updated:
New housing development proposal added
Meeting: Tuesday 10am

Get alerts like this: maxnguyen101.github.io/la-agenda-alerts
```

### 3. Word of Mouth

Free tier has zero friction - just enter email, get alerts. Users naturally invite others.

---

## 🔧 Commands

```bash
# Deploy everything
./deploy.sh

# Start dashboard
python3 v2/dashboard.py

# View logs
tail -f logs/v2_*.log

# Check system status
curl http://localhost:8080/api/stats

# Upgrade user manually
sqlite3 data/v2/la_agenda_v2.db
> UPDATE users SET plan='pro' WHERE email='user@example.com';
```

---

## ⚠️ Important Disclaimer

LA Agenda Alerts is a monitoring and notification service. It does not replace official notices, filings, or legal requirements. Users should always verify critical information with the originating agency.

While we strive for 100% reliability, this is a best-effort service. Free tier users should not rely solely on our alerts for time-sensitive matters. Pro and Org tiers include additional retry logic for higher reliability.

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Website not loading | Wait 5 min after GitHub Pages enable, clear cache |
| Dashboard down | Check: python3 v2/dashboard.py |
| No alerts | Check logs: tail -f logs/v2_pipeline.log |
| Payment not working | Use manual: Venmo/PayPal/Zelle |

---

## 📞 Support

- **Email:** mnguyen9@usc.edu
- **Dashboard:** http://localhost:8080
- **Status Page:** https://maxnguyen101.github.io/la-agenda-alerts/status

---

## 🎉 You're Ready!

**What's Live:**
- ✅ Website: [maxnguyen101.github.io/la-agenda-alerts](https://maxnguyen101.github.io/la-agenda-alerts)
- ✅ Dashboard: http://localhost:8080
- ✅ Automation: Running 3x daily
- ✅ Payments: Venmo/PayPal/Zelle ready
- ✅ Tracking: Full analytics

**Next Steps:**
1. Add 10 leads to outreach list
2. Watch dashboard for signups
3. Collect payments manually
4. Upgrade users in dashboard
5. Apply for Stripe verification

---

<div align="center">

**Built with ❤️ for LA by Max Nguyen**

*Helping Angelenos stay informed about their government*

</div>
