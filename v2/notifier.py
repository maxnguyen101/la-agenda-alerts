#!/usr/bin/env python3
"""
V2 Notifier - Tier-aware with retry logic
Supports email + SMS, respects plan limits
"""

import json
import logging
import os
import smtplib
import sqlite3
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional

# Setup logging
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "v2_notifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "v2" / "la_agenda_v2.db"

class V2Notifier:
    """Tier-aware notification system with retry logic."""
    
    def __init__(self):
        self.gmail_user = os.environ.get("GMAIL_USER")
        self.gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load V2 config."""
        config_path = Path(__file__).parent.parent / "config" / "v2.json"
        with open(config_path) as f:
            return json.load(f)
    
    def _get_db(self):
        """Get database connection."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _get_user_plan(self, email: str) -> str:
        """Get user's plan tier."""
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT plan FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        return user["plan"] if user else "free"
    
    def _get_retry_attempts(self, plan: str) -> int:
        """Get retry attempts based on plan."""
        return self.config.get("reliability", {}).get("retry_attempts", {}).get(plan, 1)
    
    def _get_plan_config(self, plan: str) -> Dict:
        """Get plan configuration."""
        return self.config.get("plans", {}).get(plan, {})
    
    def send_pending_notifications(self):
        """Process all pending notifications with retry logic."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Get pending notifications
        cursor.execute("""
            SELECT * FROM alerts_sent 
            WHERE status IN ('pending', 'retrying')
            AND retry_count < 5
            ORDER BY created_at ASC
        """)
        
        pending = cursor.fetchall()
        conn.close()
        
        logger.info(f"Processing {len(pending)} pending notifications")
        
        for alert in pending:
            self._process_notification(dict(alert))
    
    def _process_notification(self, alert: Dict):
        """Process a single notification with retries."""
        email = alert.get("user_id")  # In V2, user_id is email for free users
        plan = self._get_user_plan(email)
        max_retries = self._get_retry_attempts(plan)
        
        # Check retry limit
        if alert.get("retry_count", 0) >= max_retries:
            self._mark_failed(alert["id"], "Max retries exceeded")
            return
        
        # Get channels for this plan
        plan_config = self._get_plan_config(plan)
        channels = plan_config.get("channels", ["email"])
        
        success = False
        
        # Try email
        if "email" in channels and self.gmail_user:
            if self._send_email(alert):
                success = True
        
        # Try SMS for Pro+
        if not success and "sms" in channels and plan in ("pro", "org"):
            if self._send_sms(alert):
                success = True
        
        if success:
            self._mark_sent(alert["id"])
        else:
            self._increment_retry(alert["id"])
    
    def _send_email(self, alert: Dict) -> bool:
        """Send email notification."""
        try:
            subject = f"[LA Agenda] {alert['source_id']}: {alert['change_type']}"
            
            # Add disclaimer for free tier
            plan = self._get_user_plan(alert.get("user_id", ""))
            disclaimer = ""
            if plan == "free":
                disclaimer = self.config.get("disclaimers", {}).get("free_tier", "")
            
            body = f"""{alert['title']}

Source: {alert['source_id']}
Change: {alert['change_type']}
Time: {alert['sent_at']}

{disclaimer}
"""
            
            msg = MIMEMultipart()
            msg['From'] = self.gmail_user
            msg['To'] = alert.get("user_id")
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.gmail_user, self.gmail_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent to {alert['user_id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email failed: {e}")
            return False
    
    def _send_sms(self, alert: Dict) -> bool:
        """Send SMS via iMessage (Mac only)."""
        try:
            # Get SMS number from preferences
            conn = self._get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sms_number FROM preferences 
                WHERE user_id = (SELECT id FROM users WHERE email = ?)
            """, (alert.get("user_id"),))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result["sms_number"]:
                return False
            
            phone = result["sms_number"]
            message = f"📢 LA Alert: {alert['source_id']} - {alert['title'][:80]}..."
            
            script = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{phone}" of targetService
                send "{message}" to targetBuddy
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ SMS sent to {phone}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ SMS failed: {e}")
            return False
    
    def _mark_sent(self, alert_id: str):
        """Mark alert as sent."""
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerts_sent SET status = 'sent' WHERE id = ?",
            (alert_id,)
        )
        conn.commit()
        conn.close()
    
    def _mark_failed(self, alert_id: str, error: str):
        """Mark alert as failed."""
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerts_sent SET status = 'failed', error_message = ? WHERE id = ?",
            (error, alert_id)
        )
        conn.commit()
        conn.close()
    
    def _increment_retry(self, alert_id: str):
        """Increment retry count."""
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerts_sent SET retry_count = retry_count + 1, status = 'retrying' WHERE id = ?",
            (alert_id,)
        )
        conn.commit()
        conn.close()

if __name__ == "__main__":
    notifier = V2Notifier()
    notifier.send_pending_notifications()
