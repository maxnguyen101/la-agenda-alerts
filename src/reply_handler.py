#!/usr/bin/env python3
"""
Reply Handler - Checks for and processes email replies
Runs at 9am, 12pm, 3pm daily via cron
"""

import json
import logging
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

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
LOGS_DIR = Path(__file__).parent.parent / "logs"
STATE_DIR = DATA_DIR / "state"

AGENT_MAIL_API_KEY = os.environ.get("AGENT_MAIL_API_KEY")
OPERATOR_EMAIL = os.environ.get("OPERATOR_EMAIL", "mnguyen9@usc.edu")

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "replies.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

STATE_DIR.mkdir(parents=True, exist_ok=True)


class ReplyHandler:
    """Handles incoming email replies."""
    
    def __init__(self):
        self.replies_log_path = STATE_DIR / "email_replies.json"
        self.replies = []
        if self.replies_log_path.exists():
            with open(self.replies_log_path) as f:
                self.replies = json.load(f)
    
    def check_replies(self):
        """Check for new email replies."""
        logger.info("Checking for email replies...")
        
        # Note: Agent Mail API would need a 'list emails' endpoint
        # For now, we'll log that this check occurred
        # In production, you'd poll the API for new messages
        
        # Simulate checking (replace with actual API call when available)
        new_replies = self._fetch_replies_from_api()
        
        if new_replies:
            logger.info(f"Found {len(new_replies)} new replies")
            for reply in new_replies:
                self._process_reply(reply)
        else:
            logger.info("No new replies found")
        
        # Save state
        with open(self.replies_log_path, 'w') as f:
            json.dump(self.replies, f, indent=2)
    
    def _fetch_replies_from_api(self):
        """Fetch replies from Agent Mail API."""
        # This is a placeholder - Agent Mail API would need inbox access
        # For now, return empty list but log the check
        
        if not AGENT_MAIL_API_KEY:
            logger.warning("AGENT_MAIL_API_KEY not set - cannot check replies")
            return []
        
        # TODO: Implement when Agent Mail API supports inbox reading
        # headers = {"Authorization": f"Bearer {AGENT_MAIL_API_KEY}"}
        # req = urllib.request.Request("https://api.agentmail.ai/v1/inbox", headers=headers)
        # ...
        
        return []
    
    def _process_reply(self, reply):
        """Process a single reply."""
        from_email = reply.get("from", "")
        subject = reply.get("subject", "")
        body = reply.get("body", "")
        
        logger.info(f"Processing reply from {from_email}: {subject}")
        
        # Check for STOP/unsubscribe
        if any(word in body.lower() for word in ["stop", "unsubscribe", "remove", "opt out"]):
            self._handle_unsubscribe(from_email)
            return
        
        # Check for interest/positive response
        if any(word in body.lower() for word in ["interested", "yes", "sign up", "subscribe", "tell me more"]):
            self._handle_interest(from_email, reply)
            return
        
        # Generic reply - log for manual review
        self._log_reply(from_email, subject, body, "needs_review")
    
    def _handle_unsubscribe(self, email):
        """Handle unsubscribe request."""
        logger.info(f"Unsubscribe requested by {email}")
        
        # Add to unsubscribed list
        unsub_path = STATE_DIR / "unsubscribed.json"
        unsubscribed = []
        if unsub_path.exists():
            with open(unsub_path) as f:
                unsubscribed = json.load(f)
        
        unsubscribed.append({
            "email": email,
            "unsubscribed_at": datetime.now().isoformat()
        })
        
        with open(unsub_path, 'w') as f:
            json.dump(unsubscribed, f, indent=2)
        
        self._log_reply(email, "Unsubscribe Request", "User requested removal", "unsubscribed")
    
    def _handle_interest(self, email, reply):
        """Handle interested reply."""
        logger.info(f"Interest expressed by {email}")
        
        # Send follow-up with subscription link
        follow_up = """Thanks for your interest!

To subscribe to LA Agenda Alerts, just fill out this quick form:
https://maxnguyen.github.io/la-agenda-alerts/

You'll get email alerts whenever LA City Council, PLUM Committee, or County Board agendas are updated.

Let me know if you have any questions!

Best,
Max
"""
        
        # TODO: Send follow-up email
        self._log_reply(email, reply.get("subject", ""), reply.get("body", ""), "interested_followup_sent")
    
    def _log_reply(self, email, subject, body, status):
        """Log the reply for dashboard."""
        self.replies.append({
            "timestamp": datetime.now().isoformat(),
            "from": email,
            "subject": subject,
            "preview": body[:200] + "..." if len(body) > 200 else body,
            "status": status
        })
        
        logger.info(f"Reply logged: {email} - {status}")


def main():
    handler = ReplyHandler()
    handler.check_replies()
    logger.info("Reply check completed")


if __name__ == "__main__":
    main()
