# LA Agenda Alerts - V2 Production Ready

**Automated government monitoring for Los Angeles**  
Real-time alerts for City Council, County Board, Planning Commission, and 10 more sources.

[![Deploy](https://img.shields.io/badge/Live-GitHub%20Pages-blue)](https://maxnguyen.github.io/la-agenda-alerts)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🚀 QUICK START (Deploy in 5 Minutes)

```bash
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts
./deploy.sh
```

This will:
1. ✅ Deploy website to GitHub Pages
2. ✅ Start V2 Dashboard (localhost:8080)
3. ✅ Start Stripe Webhook Server (localhost:8081)
4. ✅ Initialize all tracking

Then:
- Enable GitHub Pages in [repository settings](https://github.com/maxnguyen/la-agenda-alerts/settings/pages)
- Visit your live site: `https://maxnguyen.github.io/la-agenda-alerts`

---

## 💰 MONETIZATION

### Pricing Tiers

| Feature | Free | Pro ($9/mo) | Org ($39/mo) |
|---------|------|-------------|--------------|
| **Alerts** | Email only | Email + SMS | Email + SMS |
| **Sources** | 13 sources | 13 sources | 13 sources |
| **Recipients** | 1 | 2 | 5 |
| **Keywords** | Basic OR | AND/OR/NOT | Team shared |
| **Calendar** | ❌ | ✅ .ics files | ✅ Shared |
| **Retries** | 1 | 3 | 5 |
| **Support** | Best-effort | Standard | Priority |

### Payment Processing

**For Now (Beta):**
- Manual payment: Venmo, PayPal, Zelle
- You manually upgrade users in dashboard
- Email: mnguyen9@usc.edu

**Soon (Stripe Verified):**
- Self-service checkout
- Automatic account upgrades
- Subscription management

---

## 🏗️ ARCHITECTURE

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Pages   │────▶│   Your Mac Mini │────▶│     Stripe      │
│  (Static Site)  │     │  (V2 Backend)   │     │   (Payments)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
   Landing Page           Dashboard API            Webhook Handler
   Pricing Info           User Management          Payment Events
   Signup Form            Alert Processing         Auto-upgrades
```

**Components:**
- **Web**: Static landing page (GitHub Pages)
- **V2 Backend**: Python dashboard + webhook server (Mac Mini)
- **Database**: SQLite with WAL mode
- **Notifications**: Gmail SMTP + iMessage backup
- **Payments**: Stripe (manual for now)

---

## 📊 DASHBOARD

**URL:** http://localhost:8080

**Features:**
- Real-time user stats by tier
- Source health monitoring (13 sources)
- Alerts sent tracking
- Outreach activity log
- System logs viewer
- Failed scrape monitoring

**Auto-refreshes every 30 seconds**

---

## 🔄 AUTOMATION

### Cron Schedule

```bash
# Agenda monitoring (3x daily)
0 8,13,18 * * *  python3 v2/pipeline.py

# Health checks (every 6 hours)
0 */6 * * *      python3 v2/health_monitor.py

# Weekly report (Sunday 9am)
0 9 * * 0        python3 v2/weekly_digest.py

# Dashboard keepalive (every 30 min)
*/30 * * * *     curl http://localhost:8080/api/health
```

### What Happens Automatically

1. **8am, 1pm, 6pm**: Checks all 13 government sources
2. **Detects changes**: Compares to previous version
3. **Matches users**: Based on keywords and preferences
4. **Sends alerts**: Email (all tiers) + SMS (Pro+)
5. **Logs everything**: Full audit trail

---

## 📁 FILE STRUCTURE

```
la-agenda-alerts/
├── web/                    # Static website (GitHub Pages)
│   └── index.html         # Landing page with pricing
├── v2/                    # V2 Backend (Mac Mini)
│   ├── dashboard.py       # Admin dashboard server
│   ├── stripe_server.py   # Payment webhook handler
│   ├── pipeline.py        # Core automation
│   ├── notifier.py        # Tier-aware alerts
│   ├── auth.py            # Magic link auth
│   ├── outreach.py        # Safe outreach system
│   └── health_monitor.py  # Source reliability
├── config/
│   └── v2.json           # Feature flags & pricing
├── data/v2/              # SQLite database
│   └── la_agenda_v2.db
├── docs/                 # Documentation
├── deploy.sh             # One-command deployment
└── setup.sh              # Initial setup
```

---

## 🎯 GETTING CUSTOMERS

### 1. Manual Outreach (Safe Mode)

Add leads to `~/Downloads/outreach_leads.txt`:
```
email@example.com - Name, description/justification
```

System will:
- Rate limit to 5/day
- Require justification
- Log all activity
- Skip if already contacted

### 2. Twitter/LinkedIn

Post alerts publicly:
```
🏛️ LA City Council agenda updated:
New housing development proposal added
Meeting: Tuesday 10am

Get alerts like this: maxnguyen.github.io/la-agenda-alerts
```

### 3. Word of Mouth

Beta users invite others:
- Free tier has no friction
- Just enter email, get alerts
- Upgrade to Pro for SMS

---

## 💵 MAKING MONEY

### First 10 Customers (Manual)

1. **Find leads**: Housing advocates, planners, journalists
2. **Add to outreach list**: `~/Downloads/outreach_leads.txt`
3. **System sends personalized emails** (automated)
4. **They reply interested** → You send payment link
5. **Payment received** → Upgrade in dashboard

### Scaling to 100+ (Stripe Automation)

1. Create Stripe account
2. Get verified for payments
3. Update `deploy.sh` with Stripe keys
4. Webhooks auto-upgrade users
5. Self-service checkout

**Revenue Projections:**
- 10 Pro users: $90/month
- 50 Pro users: $450/month
- 100 Pro + 10 Org: $1,290/month

---

## 🛠️ COMMANDS

```bash
# Deploy everything
./deploy.sh

# Start dashboard manually
python3 v2/dashboard.py

# Start Stripe server manually
python3 v2/stripe_server.py

# View logs
tail -f logs/v2_*.log

# Check system status
curl http://localhost:8080/api/stats

# View cron jobs
crontab -l
```

---

## 🔒 SAFETY FEATURES

- ✅ Outreach disabled by default
- ✅ Allowlist-only when enabled
- ✅ 5 emails/day max
- ✅ Justification required
- ✅ Full audit logging
- ✅ Best-effort disclaimer on Free tier
- ✅ Retry logic (Pro gets 3 tries, Org gets 5)

---

## 📞 SUPPORT

**Questions?**
- Email: mnguyen9@usc.edu
- Dashboard: http://localhost:8080

**Issues?**
- Check logs: `tail -f logs/*.log`
- Restart: `./deploy.sh`

---

## 🎉 YOU'RE READY!

**What's Live:**
- ✅ Website (GitHub Pages)
- ✅ Dashboard (localhost:8080)
- ✅ Automation (cron jobs)
- ✅ Payments (manual for now)
- ✅ Tracking (full analytics)

**Next Steps:**
1. Deploy: `./deploy.sh`
2. Enable GitHub Pages in settings
3. Add 10 leads to outreach list
4. Watch dashboard for signups
5. Collect payments manually
6. Upgrade users in dashboard

**Then:**
- Apply for Stripe verification
- Automate payment flow
- Scale to 100+ users

---

**Built with ❤️ for LA by Max Nguyen**  
*Helping Angelenos stay informed about their government*
