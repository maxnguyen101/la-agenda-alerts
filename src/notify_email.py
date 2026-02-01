#!/usr/bin/env python3
"""
Email notification worker: Sends alerts via Agent Mail API.
Uses AGENT_MAIL_API_KEY from environment.
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
STATE_DIR = DATA_DIR / "state"
OUTBOX_DIR = DATA_DIR / "outbox"
LOGS_DIR = Path(__file__).parent.parent / "logs"

AGENT_MAIL_API_KEY = os.environ.get("AGENT_MAIL_API_KEY")
AGENT_MAIL_API_URL = "https://api.agentmail.ai/v1/send"

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "email.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends email notifications via Agent Mail API."""
    
    def __init__(self):
        self.queue_path = STATE_DIR / "notification_queue.json"
        self.sent_log_path = STATE_DIR / "alerts_sent.json"
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        
        if not AGENT_MAIL_API_KEY:
            logger.error("AGENT_MAIL_API_KEY not set!")
    
    def send_notifications(self) -> List[Dict]:
        """Send all pending notifications."""
        
        if not AGENT_MAIL_API_KEY:
            logger.error("Cannot send: AGENT_MAIL_API_KEY not configured")
            self._save_to_outbox()
            return []
        
        if not self.queue_path.exists():
            logger.info("No notifications to send")
            return []
        
        with open(self.queue_path) as f:
            queue = json.load(f)
        
        if not queue:
            logger.info("Notification queue is empty")
            return []
        
        sent = []
        failed = []
        
        for notification in queue:
            if notification.get("status") == "pending":
                result = self._send_notification(notification)
                if result["success"]:
                    notification["status"] = "sent"
                    notification["sent_at"] = datetime.now().isoformat()
                    notification["message_id"] = result.get("message_id")
                    sent.append(notification)
                else:
                    notification["status"] = "failed"
                    notification["error"] = result.get("error")
                    failed.append(notification)
        
        # Save updated queue
        with open(self.queue_path, 'w') as f:
            json.dump(queue, f, indent=2)
        
        # Log sent notifications
        self._log_sent(sent)
        
        # Save failed to outbox
        if failed:
            self._save_failed_to_outbox(failed)
        
        logger.info(f"Sent: {len(sent)}, Failed: {len(failed)}")
        return sent
    
    def _send_notification(self, notification: Dict) -> Dict:
        """Send a single notification via Agent Mail API."""
        change = notification["change"]
        
        subject = self._build_subject(change)
        body = self._build_body(change, notification["email"])
        
        payload = {
            "to": notification["email"],
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
                AGENT_MAIL_API_URL,
                data=json.dumps(payload).encode(),
                headers=headers,
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                logger.info(f"Sent to {notification['email']}: {result.get('message_id', 'unknown')}")
                return {"success": True, "message_id": result.get("message_id")}
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"HTTP error sending to {notification['email']}: {e.code} - {error_body}")
            return {"success": False, "error": f"HTTP {e.code}: {error_body}"}
        except Exception as e:
            logger.error(f"Failed sending to {notification['email']}: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_subject(self, change: Dict) -> str:
        """Build email subject line."""
        source_names = {
            "county_bos": "LA County BOS",
            "city_council": "LA City Council",
            "plum_committee": "PLUM Committee"
        }
        
        source = source_names.get(change["source"], change["source"])
        change_type = change["change_type"].replace("_", " ").title()
        
        return f"[LA Agenda] {source}: {change_type}"
    
    def _build_body(self, change: Dict, recipient_email: str) -> str:
        """Build email body."""
        lines = [
            "LA Agenda Alert",
            "=" * 40,
            "",
            f"Change Type: {change['change_type'].replace('_', ' ').title()}",
            f"Source: {change['source']}",
            f"Title: {change['title']}",
            ""
        ]
        
        if change.get("meeting_datetime"):
            lines.append(f"Meeting: {change['meeting_datetime']}")
            lines.append("")
        
        if change.get("attachment"):
            attach = change["attachment"]
            lines.append(f"Attachment: {attach.get('name', 'Unnamed')}")
            if attach.get("url"):
                lines.append(f"Link: {attach['url']}")
            lines.append("")
        
        if change.get("source_url"):
            lines.append(f"Source: {change['source_url']}")
            lines.append("")
        
        lines.extend([
            "=" * 40,
            "",
            "Detected: " + change.get("detected_at", "Unknown"),
            "",
            "To unsubscribe or change preferences, reply to this email with STOP",
            "or contact: " + os.environ.get("OPERATOR_EMAIL", "operator@example.com"),
            "",
            "This is an automated alert from LA Agenda Alerts."
        ])
        
        return "\n".join(lines)
    
    def _log_sent(self, sent: List[Dict]):
        """Append sent notifications to log."""
        existing = []
        if self.sent_log_path.exists():
            try:
                with open(self.sent_log_path) as f:
                    existing = json.load(f)
            except:
                pass
        
        existing.extend(sent)
        
        with open(self.sent_log_path, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def _save_to_outbox(self):
        """Save queue to outbox when API key not available."""
        if not self.queue_path.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outbox_path = OUTBOX_DIR / f"queue_{timestamp}.json"
        
        import shutil
        shutil.copy(self.queue_path, outbox_path)
        logger.info(f"Saved unsent queue to {outbox_path}")
    
    def _save_failed_to_outbox(self, failed: List[Dict]):
        """Save failed notifications to outbox."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outbox_path = OUTBOX_DIR / f"failed_{timestamp}.json"
        
        with open(outbox_path, 'w') as f:
            json.dump(failed, f, indent=2)
        
        logger.info(f"Saved {len(failed)} failed notifications to {outbox_path}")


def main():
    """Main entry point."""
    if not AGENT_MAIL_API_KEY:
        logger.error("AGENT_MAIL_API_KEY environment variable required")
        # Don't exit with error - outbox handles this
    
    notifier = EmailNotifier()
    sent = notifier.send_notifications()
    
    print(json.dumps(sent, indent=2))


if __name__ == "__main__":
    main()
