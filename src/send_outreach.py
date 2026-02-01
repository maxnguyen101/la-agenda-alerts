#!/usr/bin/env python3
"""
Outreach email sender - Sends personalized emails to leads.
Usage: python3 src/send_outreach.py --dry-run (preview)
       python3 src/send_outreach.py --send (actually send)
"""

import argparse
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# Configuration
OUTREACH_DIR = Path(__file__).parent.parent / "outreach"
LOGS_DIR = Path(__file__).parent.parent / "logs"

AGENT_MAIL_API_KEY = os.environ.get("AGENT_MAIL_API_KEY")
OPERATOR_EMAIL = os.environ.get("OPERATOR_EMAIL", "mnguyen9@usc.edu")

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "outreach.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OutreachSender:
    """Manages personalized outreach emails."""
    
    def __init__(self):
        self.leads_path = OUTREACH_DIR / "leads.json"
        self.sent_path = OUTREACH_DIR / "sent.json"
        
        # Load leads
        if not self.leads_path.exists():
            logger.error("No leads.json found. Create it from leads_template.json")
            sys.exit(1)
        
        with open(self.leads_path) as f:
            data = json.load(f)
            self.leads = data.get("leads", [])
        
        # Load sent tracking
        self.sent = []
        if self.sent_path.exists():
            with open(self.sent_path) as f:
                self.sent = json.load(f)
    
    def preview_emails(self):
        """Show all pending emails without sending."""
        pending = [l for l in self.leads if l.get("status") == "pending"]
        
        if not pending:
            print("No pending leads to contact.")
            return
        
        print(f"\n{'='*60}")
        print(f"PREVIEW: {len(pending)} emails ready to send")
        print(f"{'='*60}\n")
        
        for i, lead in enumerate(pending, 1):
            email = self._craft_email(lead)
            print(f"\n{i}. To: {lead['email']}")
            print(f"   Subject: {email['subject']}")
            print(f"   Body:\n{email['body']}")
            print(f"   {'-'*60}")
    
    def send_emails(self, limit=10):
        """Send pending emails (max 10 per run)."""
        if not AGENT_MAIL_API_KEY:
            logger.error("AGENT_MAIL_API_KEY not set")
            return
        
        pending = [l for l in self.leads if l.get("status") == "pending"][:limit]
        
        if not pending:
            print("No pending leads to contact.")
            return
        
        print(f"\nSending {len(pending)} emails...")
        print("Press Ctrl+C within 3 seconds to cancel...")
        import time
        time.sleep(3)
        
        sent_count = 0
        for lead in pending:
            if self._send_single(lead):
                lead["status"] = "sent"
                lead["sent_at"] = datetime.now().isoformat()
                sent_count += 1
                
                # Track in sent log
                self.sent.append({
                    "email": lead["email"],
                    "sent_at": lead["sent_at"],
                    "status": "sent"
                })
        
        # Save updated leads
        with open(self.leads_path, 'w') as f:
            json.dump({"leads": self.leads}, f, indent=2)
        
        # Save sent log
        with open(self.sent_path, 'w') as f:
            json.dump(self.sent, f, indent=2)
        
        print(f"\n✅ Sent {sent_count} emails")
        print(f"📊 Total sent: {len(self.sent)}")
    
    def _craft_email(self, lead: dict) -> dict:
        """Create personalized email for a lead."""
        name = lead.get("name", "there")
        reason = lead.get("reason", "")
        
        # Extract domain for personalization
        domain = lead["email"].split("@")[-1]
        org = domain.split(".")[0].title() if domain else "your organization"
        
        subject = "Quick question about LA government meetings"
        
        body = f"""Hi {name},

I came across your work with {reason}. I built a simple tool that monitors LA City Council, PLUM Committee, and County Board agendas - sending email alerts when new items are posted.

It's free during beta. Thought it might save you time tracking relevant meetings.

Interested? https://maxnguyen.github.io/la-agenda-alerts/

If not, just reply STOP and I won't email again.

Best,
Max
--
LA Agenda Alerts
mnguyen9@usc.edu
"""
        
        return {"subject": subject, "body": body}
    
    def _send_single(self, lead: dict) -> bool:
        """Send a single email."""
        email = self._craft_email(lead)
        
        payload = {
            "to": lead["email"],
            "subject": email["subject"],
            "body": email["body"],
            "from": "mnguyen9@usc.edu",
            "reply_to": "mnguyen9@usc.edu"
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
                logger.info(f"Sent to {lead['email']}: {result.get('message_id')}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send to {lead['email']}: {e}")
            lead["status"] = "failed"
            lead["error"] = str(e)
            return False


def main():
    parser = argparse.ArgumentParser(description="Send outreach emails")
    parser.add_argument("--preview", action="store_true", help="Preview emails without sending")
    parser.add_argument("--send", action="store_true", help="Actually send emails (max 10)")
    parser.add_argument("--limit", type=int, default=10, help="Max emails to send")
    
    args = parser.parse_args()
    
    sender = OutreachSender()
    
    if args.preview:
        sender.preview_emails()
    elif args.send:
        sender.send_emails(limit=args.limit)
    else:
        print("Usage:")
        print("  python3 src/send_outreach.py --preview  # Preview emails")
        print("  python3 src/send_outreach.py --send     # Send emails (max 10)")


if __name__ == "__main__":
    main()
