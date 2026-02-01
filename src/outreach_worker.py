#!/usr/bin/env python3
"""
Outreach Worker - Researches leads and sends personalized emails
Runs at 9am, 12pm, 3pm daily via cron
"""

import json
import logging
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
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
LEADS_FILE = Path.home() / "Downloads" / "outreach_leads.txt"
PROCESSED_FILE = Path.home() / "Downloads" / "outreach_processed.txt"
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
        logging.FileHandler(LOGS_DIR / "outreach.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

STATE_DIR.mkdir(parents=True, exist_ok=True)


class OutreachWorker:
    """Researches leads and sends personalized outreach emails."""
    
    def __init__(self):
        self.sent_emails = []
        self.sent_log_path = STATE_DIR / "outreach_sent.json"
        if self.sent_log_path.exists():
            with open(self.sent_log_path) as f:
                self.sent_emails = json.load(f)
    
    def process_leads(self):
        """Main entry point - process all new leads."""
        if not LEADS_FILE.exists():
            logger.info("No leads file found")
            return
        
        leads = self._read_leads()
        if not leads:
            logger.info("No new leads to process")
            return
        
        logger.info(f"Found {len(leads)} new leads to process")
        
        for lead in leads:
            try:
                self._process_single_lead(lead)
                time.sleep(2)  # Rate limiting between emails
            except Exception as e:
                logger.error(f"Failed to process {lead.get('email', 'unknown')}: {e}")
        
        logger.info(f"Processed {len(leads)} leads")
    
    def _read_leads(self):
        """Read leads from file, skipping comments and empty lines."""
        leads = []
        
        with open(LEADS_FILE) as f:
            lines = f.readlines()
        
        # Filter out processed emails
        processed_emails = set()
        if PROCESSED_FILE.exists():
            with open(PROCESSED_FILE) as f:
                for line in f:
                    if '|' in line:
                        email = line.split('|')[1].strip()
                        processed_emails.add(email)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse: email - Name, description
            match = re.match(r'([^\s|]+@[^\s|]+)\s*-\s*(.+)', line)
            if match:
                email = match.group(1).strip()
                info = match.group(2).strip()
                
                if email in processed_emails:
                    continue
                
                # Parse name and description
                name_parts = info.split(',', 1)
                name = name_parts[0].strip()
                description = name_parts[1].strip() if len(name_parts) > 1 else ""
                
                leads.append({
                    "email": email,
                    "name": name,
                    "description": description,
                    "raw": line
                })
        
        return leads
    
    def _process_single_lead(self, lead):
        """Research and email a single lead."""
        email = lead["email"]
        name = lead["name"]
        
        logger.info(f"Processing: {name} ({email})")
        
        # Research the person/organization
        research_summary = self._research_lead(lead)
        
        # Generate personalized email
        email_content = self._generate_email(lead, research_summary)
        
        # Send the email
        success = self._send_email(email, email_content)
        
        # Record in processed file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "sent" if success else "failed"
        
        with open(PROCESSED_FILE, 'a') as f:
            f.write(f"{timestamp} | {email} | {name} | {research_summary[:100]}... | {email_content['subject']} | {status}\n")
        
        # Log to JSON for dashboard
        self.sent_emails.append({
            "timestamp": timestamp,
            "email": email,
            "name": name,
            "subject": email_content["subject"],
            "research_summary": research_summary,
            "status": status
        })
        
        with open(self.sent_log_path, 'w') as f:
            json.dump(self.sent_emails, f, indent=2)
        
        logger.info(f"Completed: {name} - {status}")
    
    def _research_lead(self, lead):
        """Research the lead online."""
        name = lead["name"]
        email = lead["email"]
        description = lead.get("description", "")
        
        # Extract domain for company research
        domain = email.split('@')[-1]
        company = domain.replace('.com', '').replace('.org', '').replace('.net', '').title()
        
        research_points = []
        
        # Add what we know
        if description:
            research_points.append(f"Known as: {description}")
        
        research_points.append(f"Associated with: {company}")
        
        # Try to get more info via web search if name seems like a person
        if ' ' in name and len(name.split()) >= 2:
            try:
                search_query = f"{name} {company}"
                # Note: In a real implementation, we'd use a search API
                # For now, we'll construct likely scenarios
                if "advocat" in description.lower() or "activist" in description.lower():
                    research_points.append("Community advocacy work")
                if "planning" in description.lower() or "urban" in description.lower():
                    research_points.append("Urban planning/development focus")
                if "housing" in description.lower():
                    research_points.append("Housing policy interest")
                if "nonprofit" in description.lower() or ".org" in email:
                    research_points.append("Nonprofit organization")
            except Exception as e:
                logger.warning(f"Research error for {name}: {e}")
        
        return " | ".join(research_points)
    
    def _generate_email(self, lead, research_summary):
        """Generate personalized email based on research."""
        name = lead["name"].split()[0] if ' ' in lead["name"] else lead["name"]
        description = lead.get("description", "")
        
        # Extract key terms for personalization
        personalization = ""
        if "advocat" in description.lower() or "activist" in description.lower():
            personalization = "I noticed your advocacy work in the LA community"
        elif "planning" in description.lower():
            personalization = "Your work in urban planning caught my attention"
        elif "housing" in description.lower():
            personalization = "I saw you're involved with housing issues in LA"
        elif "nonprofit" in description.lower() or ".org" in lead["email"]:
            personalization = "Your organization's community work is impressive"
        elif "consultant" in description.lower() or "firm" in description.lower():
            personalization = "I came across your firm while researching LA development"
        else:
            personalization = "I found your work related to LA local government"
        
        subject = "Quick question about LA government meetings"
        
        body = f"""Hi {name},

{personalization}.

I built a free tool that monitors LA City Council, PLUM Committee, and County Board agendas - sending email alerts when new items are posted. It saves hours of manually checking government websites.

Given your involvement with {description if description else "local issues"}, I thought this might help you track relevant meetings without the hassle.

Check it out: https://maxnguyen.github.io/la-agenda-alerts/

If it's not useful for you, no worries - just reply STOP and I won't email again.

Best,
Max
--
LA Agenda Alerts | mnguyen9@usc.edu
"""
        
        return {"subject": subject, "body": body}
    
    def _send_email(self, to_email, content):
        """Send email via Agent Mail API."""
        if not AGENT_MAIL_API_KEY:
            logger.error("AGENT_MAIL_API_KEY not set")
            return False
        
        payload = {
            "to": to_email,
            "subject": content["subject"],
            "body": content["body"],
            "from": OPERATOR_EMAIL,
            "reply_to": OPERATOR_EMAIL
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
                logger.info(f"Email sent to {to_email}: {result.get('message_id')}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send to {to_email}: {e}")
            return False


def main():
    worker = OutreachWorker()
    worker.process_leads()
    logger.info("Outreach worker completed")


if __name__ == "__main__":
    main()
