#!/usr/bin/env python3
"""
Operator notification worker: Sends alerts on failures.
Uses email (Agent Mail) and iMessage (AppleScript).
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
STATE_DIR = DATA_DIR / "state"
LOGS_DIR = Path(__file__).parent.parent / "logs"

OPERATOR_EMAIL = os.environ.get("OPERATOR_EMAIL", "")
OPERATOR_IMESSAGE = os.environ.get("OPERATOR_IMESSAGE", "")
AGENT_MAIL_API_KEY = os.environ.get("AGENT_MAIL_API_KEY")

FAILURE_THRESHOLD = 3  # Alert after 3 consecutive failures

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "operator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OperatorNotifier:
    """Notifies operator of system issues."""
    
    def __init__(self):
        self.failures_path = STATE_DIR / "source_failures.json"
        self.operator_log = LOGS_DIR / "operator_alerts.log"
    
    def check_and_notify(self, source_results: List[Dict]):
        """Check for failures and notify operator if threshold reached."""
        # Load failure history
        failures = self._load_failures()
        
        alerts_needed = []
        
        for result in source_results:
            source_id = result.get("source_id")
            urls = result.get("urls", [])
            
            # Check if all URLs failed
            all_failed = all(url.get("status") == "error" for url in urls)
            
            if all_failed:
                failures[source_id] = failures.get(source_id, 0) + 1
                
                if failures[source_id] >= FAILURE_THRESHOLD:
                    alerts_needed.append({
                        "source_id": source_id,
                        "source_name": result.get("source_name", source_id),
                        "consecutive_failures": failures[source_id]
                    })
            else:
                # Reset counter on success
                if source_id in failures:
                    del failures[source_id]
        
        # Save updated failures
        self._save_failures(failures)
        
        # Send alerts
        for alert in alerts_needed:
            self._send_alert(alert)
    
    def _load_failures(self) -> Dict:
        """Load failure counts."""
        if not self.failures_path.exists():
            return {}
        
        try:
            with open(self.failures_path) as f:
                return json.load(f)
        except:
            return {}
    
    def _save_failures(self, failures: Dict):
        """Save failure counts."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.failures_path, 'w') as f:
            json.dump(failures, f)
    
    def _send_alert(self, alert: Dict):
        """Send alert to operator via email and iMessage."""
        subject = f"🚨 LA Agenda Alerts: {alert['source_name']} failing"
        message = (
            f"ALERT: {alert['source_name']} has failed "
            f"{alert['consecutive_failures']} consecutive times.\n\n"
            f"Source ID: {alert['source_id']}\n"
            f"Time: {datetime.now().isoformat()}\n\n"
            f"Please check logs at: logs/run.log"
        )
        
        # Send email
        if OPERATOR_EMAIL and AGENT_MAIL_API_KEY:
            self._send_email(subject, message)
        
        # Send iMessage
        if OPERATOR_IMESSAGE:
            self._send_imessage(message)
        
        # Log alert
        self._log_alert(alert)
    
    def _send_email(self, subject: str, body: str):
        """Send email via Agent Mail."""
        import urllib.request
        
        payload = {
            "to": OPERATOR_EMAIL,
            "subject": subject,
            "body": body,
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
                logger.info(f"Operator email sent: {result.get('message_id')}")
                
        except Exception as e:
            logger.error(f"Failed to send operator email: {e}")
    
    def _send_imessage(self, message: str):
        """Send iMessage via AppleScript."""
        if not OPERATOR_IMESSAGE:
            return
        
        try:
            script = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{OPERATOR_IMESSAGE}" of targetService
                send "{message}" to targetBuddy
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"iMessage sent to {OPERATOR_IMESSAGE}")
            else:
                logger.error(f"iMessage failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Failed to send iMessage: {e}")
    
    def _log_alert(self, alert: Dict):
        """Log operator alert."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "alert": alert
        }
        
        with open(self.operator_log, 'a') as f:
            f.write(json.dumps(entry) + "\n")


def main():
    """Main entry point - called after fetch."""
    manifest_path = STATE_DIR / "../raw"  # Will find latest
    
    # Find latest manifest
    run_dirs = sorted(Path(DATA_DIR / "raw").glob("*/*/"))
    if not run_dirs:
        logger.warning("No fetch runs found")
        return
    
    latest_manifest = run_dirs[-1] / "manifest.json"
    
    if not latest_manifest.exists():
        logger.warning("No manifest found")
        return
    
    with open(latest_manifest) as f:
        manifest = json.load(f)
    
    notifier = OperatorNotifier()
    notifier.check_and_notify(manifest.get("sources", []))


if __name__ == "__main__":
    main()
