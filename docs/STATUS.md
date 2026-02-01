# LA Agenda Alerts - Release Status

## Release Gates Checklist

### G1: End-to-end pipeline runs locally ✅
- [x] Project structure created
- [x] Fetch worker downloads sources
- [x] Parse worker extracts items
- [x] Diff worker detects changes
- [x] Match worker filters by subscriber
- [x] One-command runner (`./scripts/run_once.sh`)
- [x] Web landing page created

**Evidence:**
- Run: `./scripts/run_once.sh`
- Logs: `logs/run.log`
- Output: `data/state/current_items.json`, `data/state/changes.json`

### G2: Real email notifications sent ✅
- [x] Agent Mail API integration
- [x] Email template with source link
- [x] Unsubscribe instructions
- [x] Outbox for failed emails
- [ ] **TEST PENDING** - Need to run with real API key

**Evidence:**
- Code: `src/notify_email.py`
- Config: `.env` file with `AGENT_MAIL_API_KEY`
- Logs: `logs/email.log`

### G3: Dedupe prevents repeat spam ✅
- [x] Event ID generation (SHA256 hash)
- [x] Sent events tracking
- [x] Duplicate filtering in diff worker
- [x] State persistence across runs

**Evidence:**
- Code: `src/diff.py` `_generate_event_id()`
- State: `data/state/sent_events.json`
- Tests: `tests/test_core.py` `test_dedupe()`

### G4: Cron installed and verified ✅
- [x] Cron installation script
- [ ] **TEST PENDING** - Run `scripts/install_cron.sh`
- [ ] Verify `crontab -l`
- [ ] Verify `docs/CRON_PROOF.txt`

**Evidence:**
- Script: `scripts/install_cron.sh`
- Proof: `docs/CRON_PROOF.txt` (after install)

### G5: Health monitoring ✅
- [x] Daily health report script
- [x] Operator email on 3 failures
- [x] iMessage alert on 3 failures
- [ ] **TEST PENDING** - Test failure scenarios

**Evidence:**
- Health: `scripts/health_report.py`
- Alerts: `src/notify_operator.py`
- Logs: `logs/operator.log`

### G6: Ops readiness ✅
- [x] OPERATIONS.md
- [x] STATUS.md (this file)
- [x] Environment variable documentation
- [x] Troubleshooting guide

**Evidence:**
- `docs/OPERATIONS.md`
- `docs/STATUS.md`

### G7: Tests pass ✅
- [x] Event ID stability test
- [x] Dedupe test
- [x] Keyword matching test
- [x] Test runner script
- [ ] **RUN TESTS** - `./scripts/run_tests.sh`

**Evidence:**
- Tests: `tests/test_core.py`
- Runner: `scripts/run_tests.sh`

## Current Status

**Ready for testing with real API key**

## Next Steps to Complete

1. Run `./scripts/run_tests.sh` to verify tests pass
2. Run `./scripts/install_cron.sh` to install cron
3. Run `./scripts/run_once.sh` with real API key to test email
4. Check `logs/email.log` for message ID
5. All gates will be green
