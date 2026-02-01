# LA Agenda Alerts - Operations Guide

## Prerequisites

- Python 3.11+
- macOS (for iMessage operator alerts)
- Environment variables configured in `.env` file

## Required Environment Variables

Create a `.env` file in the project root:

```bash
AGENT_MAIL_API_KEY=your_api_key_here
OPERATOR_EMAIL=youremail@example.com
OPERATOR_IMESSAGE=your@email.com
```

## How to Run

### Run Once (Manual)

```bash
./scripts/run_once.sh
```

This executes the full pipeline:
1. Fetch sources
2. Parse content
3. Detect changes
4. Match to subscribers
5. Send notifications
6. Update state

### View Logs

```bash
# View main run log
tail -f logs/run.log

# View email log
tail -f logs/email.log

# View operator alerts
tail -f logs/operator.log
```

## Install Cron (Automated Runs)

```bash
./scripts/install_cron.sh
```

This installs:
- Checks at 8:00 AM, 1:00 PM, 6:00 PM daily
- Health report at 7:00 AM daily

Verify installation:
```bash
crontab -l
cat docs/CRON_PROOF.txt
```

## Remove Cron

```bash
crontab -e
# Delete the LA Agenda Alerts section
```

## Add a Subscriber

Edit `data/subscribers.json`:

```json
{
  "subscribers": [
    {
      "id": "unique_id",
      "email": "subscriber@example.com",
      "keywords": ["housing", "zoning"],
      "sources": ["city_council", "county_bos"],
      "frequency": "instant",
      "status": "active",
      "created_at": "2026-02-01T00:00:00Z"
    }
  ]
}
```

## Pause a Subscriber

Change `status` from `"active"` to `"paused"` in `data/subscribers.json`.

## Rotate Agent Mail API Key

1. Get new key from https://agentmail.ai/
2. Update `.env` file
3. Test with: `./scripts/run_once.sh`

## Troubleshooting

### No emails sending
- Check `AGENT_MAIL_API_KEY` is set
- Check `logs/email.log` for errors
- Verify subscriber keywords match content

### iMessage not working
- Must run on macOS
- Messages app must be configured
- Check `logs/operator.log`

### Source fetch failures
- Check `logs/fetch.log`
- URLs may have changed - update `src/sources.json`
- Some government sites may block scrapers

## Data Retention

- Raw data: 30 days
- Logs: 90 days
- Sent events: Persistent (for dedupe)

## Emergency Stop

To immediately stop all operations:
```bash
./scripts/install_cron.sh  # Then remove all LA Agenda Alerts lines
# Or: crontab -r  # Removes ALL cron jobs
```
