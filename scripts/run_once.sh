#!/bin/bash
#
# Run the full LA Agenda Alerts pipeline once
# Usage: ./scripts/run_once.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOGS_DIR"

RUN_LOG="$LOGS_DIR/run.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] =======================================" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] LA Agenda Alerts - Starting run" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] =======================================" | tee -a "$RUN_LOG"

cd "$PROJECT_DIR"

# Step 1: Fetch sources
echo "[$TIMESTAMP] Step 1: Fetching sources..." | tee -a "$RUN_LOG"
if python3 src/fetch_sources.py >> "$RUN_LOG" 2>&1; then
    FETCH_STATUS="SUCCESS"
else
    FETCH_STATUS="FAILED"
fi
echo "[$TIMESTAMP] Fetch: $FETCH_STATUS" | tee -a "$RUN_LOG"

# Step 2: Parse sources
echo "[$TIMESTAMP] Step 2: Parsing sources..." | tee -a "$RUN_LOG"
if python3 src/parse_sources.py >> "$RUN_LOG" 2>&1; then
    PARSE_STATUS="SUCCESS"
else
    PARSE_STATUS="FAILED"
fi
echo "[$TIMESTAMP] Parse: $PARSE_STATUS" | tee -a "$RUN_LOG"

# Step 3: Diff changes
echo "[$TIMESTAMP] Step 3: Running diff..." | tee -a "$RUN_LOG"
if python3 src/diff.py >> "$RUN_LOG" 2>&1; then
    DIFF_STATUS="SUCCESS"
else
    DIFF_STATUS="FAILED"
fi
echo "[$TIMESTAMP] Diff: $DIFF_STATUS" | tee -a "$RUN_LOG"

# Step 4: Match to subscribers
echo "[$TIMESTAMP] Step 4: Matching to subscribers..." | tee -a "$RUN_LOG"
if python3 src/match.py >> "$RUN_LOG" 2>&1; then
    MATCH_STATUS="SUCCESS"
else
    MATCH_STATUS="FAILED"
fi
echo "[$TIMESTAMP] Match: $MATCH_STATUS" | tee -a "$RUN_LOG"

# Step 5: Send notifications (if API key available)
echo "[$TIMESTAMP] Step 5: Sending notifications..." | tee -a "$RUN_LOG"
if [ -n "$AGENT_MAIL_API_KEY" ]; then
    if python3 src/notify_email.py >> "$RUN_LOG" 2>&1; then
        NOTIFY_STATUS="SUCCESS"
    else
        NOTIFY_STATUS="FAILED"
    fi
else
    echo "[$TIMESTAMP] AGENT_MAIL_API_KEY not set - skipping email" | tee -a "$RUN_LOG"
    NOTIFY_STATUS="SKIPPED"
fi
echo "[$TIMESTAMP] Notify: $NOTIFY_STATUS" | tee -a "$RUN_LOG"

# Step 6: Update state (only if notify succeeded)
if [ "$NOTIFY_STATUS" = "SUCCESS" ]; then
    echo "[$TIMESTAMP] Step 6: Updating state..." | tee -a "$RUN_LOG"
    cp data/state/current_items.json data/state/last_items.json
    echo "[$TIMESTAMP] State updated" | tee -a "$RUN_LOG"
fi

# Summary
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] =======================================" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] RUN SUMMARY" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] =======================================" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] Fetch:   $FETCH_STATUS" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] Parse:   $PARSE_STATUS" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] Diff:    $DIFF_STATUS" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] Match:   $MATCH_STATUS" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] Notify:  $NOTIFY_STATUS" | tee -a "$RUN_LOG"
echo "[$TIMESTAMP] =======================================" | tee -a "$RUN_LOG"

echo "Run complete. See $RUN_LOG for details."
