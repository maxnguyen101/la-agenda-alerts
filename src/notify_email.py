#!/usr/bin/env python3
"""
Email notification worker: Sends alerts via Gmail SMTP.
More reliable than Agent Mail API on restricted networks.
"""

import json
import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional

# Load .env file
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
OUTBOX_DIR = DATA_DIR / "outbox"
LOGS_DIR = Path(__file__).parent.parent / "logs"

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

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
    """Sends email notifications via Gmail SMTP."""
    
    def __init__(self):
        self.queue_path = STATE_DIR / "notification_queue.json"
        self.sent_log_path = STATE_DIR / "alerts_sent.json"
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        
        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            logger.error("GMAIL_USER or GMAIL_APP_PASSWORD not set!")
    
    def send_notifications(self) -> List[Dict]:
        """Send all pending notifications via Gmail."""
        
        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            logger.error("Cannot send: Gmail credentials not configured")
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
        """Send a single notification via Gmail SMTP."""
        change = notification["change"]
        to_email = notification["email"]
        
        subject = self._build_subject(change)
        body = self._build_body(change, to_email)
        
        try:
            msg = MIMEMultipart()
            msg['From'] = GMAIL_USER
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Sent to {to_email}: {subject}")
            return {"success": True, "message_id": f"gmail_{datetime.now().timestamp()}"}
            
        except Exception as e:
            logger.error(f"Failed sending to {to_email}: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_subject(self, change: Dict) -> str:
        """Build email subject line."""
        source_names = {
            "county_bos": "LA County BOS",
            "city_council": "LA City Council",
            "plum_committee": "PLUM Committee",
            "city_planning": "Planning Commission",
            "metro_board": "LA Metro Board",
            "hcidla": "LA Housing Dept",
            "rent_stabilization": "Rent Board",
            "hacola": "Housing Authority",
            "lacda": "County Development",
            "ladot": "LA DOT",
            "caltrans_d7": "Caltrans D7",
            "aqmd": "Air Quality",
            "la_sanitation": "LA Sanitation"
        }
        
        source = source_names.get(change["source"], change["source"])
        change_type = change["change_type"].replace("_", " ").title()
        
        return f"[LA Agenda] {source}: {change_type}"
    
    def _build_body(self, change: Dict, recipient_email: str) -> str:
        """Build email body."""
        lines = [
            "🏛️ LA Agenda Alert",
            "=" * 50,
            "",
            f"📋 Change Type: {change['change_type'].replace('_', ' ').title()}",
            f"🏢 Source: {change['source']}",
            f"📌 Title: {change['title']}",
            ""
        ]
        
        if change.get("meeting_datetime"):
            lines.append(f"📅 Meeting: {change['meeting_datetime']}")
            lines.append("")
        
        if change.get("attachment"):
            attach = change["attachment"]
            lines.append(f"📎 Attachment: {attach.get('name', 'Unnamed')}")
            if attach.get("url"):
                lines.append(f"🔗 Link: {attach['url']}")
            lines.append("")
        
        if change.get("source_url"):
            lines.append(f"🌐 Source: {change['source_url']}")
            lines.append("")
        
        lines.extend([
            "=" * 50,
            "",
            f"⏰ Detected: {change.get('detected_at', 'Unknown')}",
            "",
            "To unsubscribe or change preferences, reply to this email with STOP",
            f"or contact: {GMAIL_USER}",
            "",
            "This is an automated alert from LA Agenda Alerts.",
            "Monitor more at: https://maxnguyen.github.io/la-agenda-alerts"
        ])
        
        return "\n".join(lines)
    
    def _log_sent(self, sent: List[Dict]):
        """Log sent notifications."""
        if not sent:
            return
        
        existing = []
        if self.sent_log_path.exists():
            with open(self.sent_log_path) as f:
                existing = json.load(f)
        
        for notification in sent:
            log_entry = {
                "sent_at": notification["sent_at"],
                "email": notification["email"],
                "source": notification["change"]["source"],
                "title": notification["change"]["title"],
                "message_id": notification.get("message_id")
            }
            existing.append(log_entry)
        
        with open(self.sent_log_path, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def _save_to_outbox(self):
        """Save queue to outbox for manual processing."""
        if not self.queue_path.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outbox_path = OUTBOX_DIR / f"queue_{timestamp}.json"
        
        with open(self.queue_path) as f:
            queue = json.load(f)
        
        with open(outbox_path, 'w') as f:
            json.dump(queue, f, indent=2)
        
        logger.info(f"Saved queue to outbox: {outbox_path}")
    
    def _save_failed_to_outbox(self, failed: List[Dict]):
        """Save failed notifications to outbox."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outbox_path = OUTBOX_DIR / f"failed_{timestamp}.json"
        
        with open(outbox_path, 'w') as f:
            json.dump(failed, f, indent=2)
        
        logger.info(f"Saved failed notifications to outbox: {outbox_path}")


def main():
    notifier = EmailNotifier()
    sent = notifier.send_notifications()
    logger.info(f"Email notification worker completed: {len(sent)} sent")


if __name__ == "__main__":
    main()
