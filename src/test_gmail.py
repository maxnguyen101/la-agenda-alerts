#!/usr/bin/env python3
"""
Gmail SMTP backup for email notifications
Usage: Set GMAIL_USER and GMAIL_APP_PASSWORD in .env
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

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "gmail.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def send_test_email(to_email=None):
    """Send a test email via Gmail SMTP."""
    
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.error("GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
        logger.info("To use Gmail:")
        logger.info("1. Enable 2FA on Google account")
        logger.info("2. Generate App Password at myaccount.google.com/apppasswords")
        logger.info("3. Add to .env: GMAIL_USER=your.email@gmail.com")
        logger.info("4. Add to .env: GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx")
        return False
    
    to = to_email or GMAIL_USER
    
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to
        msg['Subject'] = "[LA Agenda Alerts] Test Email via Gmail SMTP"
        
        body = f"""This is a test email from LA Agenda Alerts using Gmail SMTP.

Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

If you're receiving this, Gmail SMTP is working correctly!

To use Gmail as your email provider:
1. Add GMAIL_USER and GMAIL_APP_PASSWORD to .env
2. Run: python3 src/notify_gmail.py

Gmail is more reliable than Agent Mail on restricted networks.

Best,
LA Agenda Alerts
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Test email sent successfully to {to}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", help="Recipient email (defaults to GMAIL_USER)")
    args = parser.parse_args()
    
    send_test_email(args.to)
