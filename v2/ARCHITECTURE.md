# LA Agenda Alerts - V2 Architecture Overview

## V2 System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    LA AGENDA ALERTS V2                      │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: DATA STORAGE (File-backed + SQLite)              │
│  ├── data/v2/                                              │
│  │   ├── users.db (SQLite) - auth, plans, preferences     │
│  │   ├── alerts.db (SQLite) - sent alerts, retries        │
│  │   └── sources.db (SQLite) - health, uptime, metrics    │
│  ├── data/state/ (JSON) - queues, ephemeral state         │
│  └── logs/ (text) - all system logs                        │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: CORE SERVICES (Python)                           │
│  ├── Fetcher (13 sources, health scoring)                 │
│  ├── Parser (content extraction)                          │
│  ├── Matcher (tier-aware keyword logic)                   │
│  ├── Notifier (email/SMS with retry logic)                │
│  └── Health Monitor (source scoring, alerts)              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: API LAYER (Flask - lightweight)                  │
│  ├── /api/auth (magic links)                              │
│  ├── /api/user (preferences, plan management)             │
│  ├── /api/alerts (history, stats)                         │
│  └── /public/status (system health page)                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: FRONTEND                                         │
│  ├── Landing page (with pricing tiers)                    │
│  ├── User dashboard (Pro+ only)                           │
│  ├── Public status page                                   │
│  └── Admin dashboard (local)                              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: OUTREACH (Safe-by-default)                       │
│  ├── Allowlist-only mode                                  │
│  ├── Rate limiting (5/day max)                            │
│  ├── Justification required                               │
│  └── Full audit logging                                   │
└─────────────────────────────────────────────────────────────┘
```

## Tier Enforcement Strategy

| Feature | Free | Pro ($9) | Org ($39) |
|---------|------|----------|-----------|
| **Recipients** | 1 email | 1 email + 1 SMS | 5 recipients |
| **Keywords** | Basic OR | AND/OR/NOT logic | Shared team sets |
| **Calendar** | No | .ics generation | .ics + shared calendar |
| **Login** | No | Magic link required | Magic link required |
| **Retries** | 1 attempt | 3 attempts | 5 attempts + priority |
| **Dashboard** | No | Personal | Team view |
| **Support** | Best-effort | Standard | Priority |

## Data Models

### User Model
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID
    email TEXT UNIQUE NOT NULL,
    plan TEXT CHECK(plan IN ('free', 'pro', 'org')),
    status TEXT CHECK(status IN ('active', 'paused', 'cancelled')),
    billing_status TEXT,           -- 'paid', 'trial', 'overdue'
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    magic_link_token TEXT,         -- temporary auth token
    magic_link_expires TIMESTAMP
);
```

### Preferences Model
```sql
CREATE TABLE preferences (
    user_id TEXT PRIMARY KEY,
    keywords TEXT,                 -- JSON array
    keyword_logic TEXT,            -- 'OR', 'AND', 'ADVANCED'
    sources TEXT,                  -- JSON array of source IDs
    frequency TEXT,                -- 'instant', 'digest', 'weekly'
    sms_number TEXT,               -- Pro+ only
    timezone TEXT DEFAULT 'America/Los_Angeles'
);
```

### Alert History Model
```sql
CREATE TABLE alerts_sent (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    source_id TEXT,
    change_type TEXT,
    title TEXT,
    sent_at TIMESTAMP,
    channel TEXT CHECK(channel IN ('email', 'sms')),
    status TEXT,                   -- 'sent', 'failed', 'retrying'
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);
```

### Source Health Model
```sql
CREATE TABLE source_health (
    source_id TEXT PRIMARY KEY,
    last_check TIMESTAMP,
    last_success TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    success_rate REAL,             -- 0.0 to 1.0
    avg_response_time_ms INTEGER,
    status TEXT CHECK(status IN ('healthy', 'degraded', 'down'))
);
```

## Config Flags (config/v2.json)

```json
{
  "features": {
    "auth_required": false,           -- Global override
    "pro_plan_enabled": true,
    "org_plan_enabled": false,        -- Launch later
    "sms_enabled": true,
    "calendar_ics_enabled": true
  },
  "outreach": {
    "enabled": false,                 -- Safe default
    "allowlist_only": true,
    "max_daily_sends": 5,
    "require_justification": true
  },
  "reliability": {
    "retry_attempts": {
      "free": 1,
      "pro": 3,
      "org": 5
    },
    "alert_timeout_hours": 24
  },
  "support": {
    "health_digest_day": "sunday",
    "error_digest_hour": 9,
    "auto_tag_errors": true
  }
}
```

## Migration Plan (V1 → V2)

### Phase 1: Database Setup (No Downtime)
1. Create SQLite databases
2. Migrate subscribers.json → users.db
3. Run parallel (V1 continues working)

### Phase 2: Gradual Cutover
1. Deploy V2 alongside V1
2. Route new signups to V2
3. Migrate existing users on login

### Phase 3: Full Cutover
1. Stop V1 cron jobs
2. Activate V2 cron jobs
3. Archive V1 data

## New/Modified Cron Jobs

```bash
# V2 Core Schedule
0 8,13,18 * * *  python3 v2/fetch.py && python3 v2/parse.py && python3 v2/match.py && python3 v2/notify.py
0 9,12,15 * * *  python3 v2/outreach.py --allowlist-only
5 9,12,15 * * *  python3 v2/reply_handler.py
0 7 * * *        python3 v2/health_report.py
0 9 * * 0        python3 v2/weekly_digest.py  # Sunday 9am

# V2 Maintenance
*/30 * * * *     curl -s http://localhost:8080/api/health > /dev/null 2>&1 || true
0 */6 * * *      python3 v2/source_health_check.py
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SQLite corruption | Daily backups, write-ahead logging |
| Auth system failure | Free tier always works without auth |
| Magic link delivery | Fallback to direct email contact |
| Pro users can't login | Bypass via admin dashboard |
| Rate limit exceeded | Queue + retry with backoff |
| Source blocking us | Rotate User-Agents, respect robots.txt |
| Outreach spam reports | Allowlist-only, low volume caps |

## Implementation Order

1. Database layer (SQLite setup)
2. Config system (feature flags)
3. User/auth system (magic links)
4. Tier enforcement (plan checks)
5. Enhanced notifier (retry logic)
6. Health monitoring (source scoring)
7. Dashboard updates (stats, reliability)
8. Outreach safety (allowlist)
9. Public status page
10. Migration scripts
