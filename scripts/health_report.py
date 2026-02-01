#!/usr/bin/env python3
"""
Daily health report: Sends summary to operator.
Run once daily (e.g., 7:00 AM).
"""

import json
import logging
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"

OPERATOR_EMAIL = os.environ.get("OPERATOR_EMAIL", "")
AGENT_MAIL_API_KEY = os.environ.get("AGENT_MAIL_API_KEY")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def generate_report() -> str:
    """Generate health report for last 24 hours."""
    report_lines = ["LA Agenda Alerts - Daily Health Report", "=" * 40, ""]
    
    # Check run logs
    run_log = LOGS_DIR / "run.log"
    runs_24h = 0
    failures_24h = 0
    
    if run_log.exists():
        cutoff = datetime.now() - timedelta(hours=24)
        
        with open(run_log) as f:
            for line in f:
                # Count runs
                if "LA Agenda Alerts - Starting run" in line:
                    try:
                        timestamp_str = line.split("]")[0].strip("[")
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        if timestamp > cutoff:
                            runs_24h += 1
                    except:
                        pass
                
                # Count failures
                if "FAILED" in line:
                    failures_24h += 1
    
    report_lines.append(f"Runs (24h): {runs_24h}")
    report_lines.append(f"Failures: {failures_24h}")
    
    # Check changes detected
    changes_path = DATA_DIR / "state" / "changes.json"
    changes_count = 0
    
    if changes_path.exists():
        try:
            with open(changes_path) as f:
                changes = json.load(f)
                # Count changes from last 24h
                cutoff = datetime.now() - timedelta(hours=24)
                for change in changes:
                    try:
                        detected = datetime.fromisoformat(change.get("detected_at", ""))
                        if detected > cutoff:
                            changes_count += 1
                    except:
                        pass
        except:
            pass
    
    report_lines.append(f"Changes detected: {changes_count}")
    
    # Check emails sent
    sent_log = DATA_DIR / "state" / "alerts_sent.json"
    emails_sent = 0
    
    if sent_log.exists():
        try:
            with open(sent_log) as f:
                sent = json.load(f)
                cutoff = datetime.now() - timedelta(hours=24)
                for entry in sent:
                    try:
                        sent_time = datetime.fromisoformat(entry.get("sent_at", ""))
                        if sent_time > cutoff:
                            emails_sent += 1
                    except:
                        pass
        except:
            pass
    
    report_lines.append(f"Emails sent: {emails_sent}")
    
    # Add status
    report_lines.append("")
    if failures_24h == 0 and runs_24h > 0:
        report_lines.append("Status: ✅ HEALTHY")
    elif failures_24h > 0:
        report_lines.append(f"Status: ⚠️ {failures_24h} failures detected")
    else:
        report_lines.append("Status: ℹ️ No runs in last 24h")
    
    report_lines.append("")
    report_lines.append(f"Report generated: {datetime.now().isoformat()}")
    report_lines.append("")
    report_lines.append("View full logs: logs/run.log")
    
    return "\n".join(report_lines)


def send_report(report: str):
    """Send report via Agent Mail."""
    if not OPERATOR_EMAIL or not AGENT_MAIL_API_KEY:
        logger.error("Missing OPERATOR_EMAIL or AGENT_MAIL_API_KEY")
        return
    
    payload = {
        "to": OPERATOR_EMAIL,
        "subject": "LA Agenda Alerts - Daily Health Report",
        "body": report,
        "from": "alerts@tapcare.app"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGENT_MAIL_API_KEY}"
    }
    
    try:
        req = urllib.request.Request(
            "https://api.agentmail.ai/v1/send",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            logger.info(f"Health report sent: {result.get('message_id')}")
            
    except Exception as e:
        logger.error(f"Failed to send health report: {e}")


def main():
    """Main entry point."""
    report = generate_report()
    print(report)
    print()
    
    send_report(report)


if __name__ == "__main__":
    main()
