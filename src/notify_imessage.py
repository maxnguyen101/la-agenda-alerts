#!/usr/bin/env python3
"""
iMessage notifier - Sends alerts via iMessage (bypasses email blocks)
Usage: python3 src/notify_imessage.py
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
STATE_DIR = DATA_DIR / "state"
LOGS_DIR = Path(__file__).parent.parent / "logs"

OPERATOR_IMESSAGE = os.environ.get("OPERATOR_IMESSAGE", "7148004033")

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "imessage.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class iMessageNotifier:
    """Sends iMessage notifications via macOS Messages app."""
    
    def __init__(self):
        self.queue_path = STATE_DIR / "notification_queue.json"
        self.sent_log_path = STATE_DIR / "imessage_sent.json"
        
    def send_notifications(self) -> List[Dict]:
        """Send pending notifications via iMessage."""
        
        if not self.queue_path.exists():
            logger.info("No notifications to send")
            return []
        
        with open(self.queue_path) as f:
            queue = json.load(f)
        
        if not queue:
            logger.info("Notification queue is empty")
            return []
        
        sent = []
        
        for notification in queue:
            if notification.get("status") == "pending":
                result = self._send_imessage(notification)
                if result["success"]:
                    notification["status"] = "sent_via_imessage"
                    notification["sent_at"] = datetime.now().isoformat()
                    sent.append(notification)
                    logger.info(f"iMessage sent for {notification['change']['title'][:50]}...")
                else:
                    logger.error(f"Failed to send iMessage: {result.get('error')}")
        
        # Save updated queue
        with open(self.queue_path, 'w') as f:
            json.dump(queue, f, indent=2)
        
        # Log sent
        self._log_sent(sent)
        
        return sent
    
    def _send_imessage(self, notification: Dict) -> Dict:
        """Send a single iMessage using macOS osascript."""
        change = notification["change"]
        
        # Build message
        message = self._build_message(change)
        
        # AppleScript to send iMessage
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{OPERATOR_IMESSAGE}" of targetService
            send "{message}" to targetBuddy
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_message(self, change: Dict) -> str:
        """Build iMessage text."""
        source_names = {
            "county_bos": "County BOS",
            "city_council": "City Council",
            "plum_committee": "PLUM",
            "city_planning": "Planning Commission",
            "metro_board": "Metro Board",
            "hcidla": "Housing Dept",
            "rent_stabilization": "Rent Board",
            "hacola": "Housing Authority",
            "lacda": "County Dev",
            "ladot": "DOT",
            "caltrans_d7": "Caltrans",
            "aqmd": "Air Quality",
            "la_sanitation": "Sanitation"
        }
        
        source = source_names.get(change["source"], change["source"])
        change_type = change["change_type"].replace("_", " ").title()
        
        # Truncate title for SMS
        title = change["title"][:80] + "..." if len(change["title"]) > 80 else change["title"]
        
        message = f"📢 LA Alert: {source} - {change_type}\\n\\n{title}"
        
        if change.get("meeting_datetime"):
            message += f"\\n📅 {change['meeting_datetime']}"
        
        if change.get("source_url"):
            # Shorten URL hint
            message += f"\\n🔗 Check email for full details"
        
        return message
    
    def _log_sent(self, sent: List[Dict]):
        """Log sent notifications."""
        if not sent:
            return
        
        existing = []
        if self.sent_log_path.exists():
            with open(self.sent_log_path) as f:
                existing = json.load(f)
        
        existing.extend(sent)
        
        with open(self.sent_log_path, 'w') as f:
            json.dump(existing, f, indent=2)


def main():
    notifier = iMessageNotifier()
    sent = notifier.send_notifications()
    logger.info(f"Sent {len(sent)} iMessage notifications")


if __name__ == "__main__":
    main()
