#!/usr/bin/env python3
"""
V2 Outreach System - Safe-by-default with guardrails
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "v2_outreach.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "v2" / "la_agenda_v2.db"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "v2.json"

class SafeOutreach:
    """Outreach system with safety guardrails."""
    
    def __init__(self):
        self.config = self._load_config()
        self.outreach_config = self.config.get("outreach", {})
    
    def _load_config(self) -> Dict:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    
    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def is_outreach_enabled(self) -> bool:
        """Check if outreach is enabled."""
        return self.outreach_config.get("enabled", False)
    
    def get_daily_send_count(self) -> int:
        """Get number of emails sent today."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COUNT(*) FROM outreach_log 
            WHERE date(sent_at) = date('now')
        """)
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def can_send_outreach(self, email: str, justification: str) -> tuple[bool, str]:
        """Check if outreach is allowed for this email."""
        
        # Check if outreach enabled
        if not self.is_outreach_enabled():
            return False, "Outreach is disabled by default"
        
        # Check daily limit
        daily_limit = self.outreach_config.get("max_daily_sends", 5)
        if self.get_daily_send_count() >= daily_limit:
            return False, f"Daily limit reached ({daily_limit})"
        
        # Check allowlist
        if self.outreach_config.get("allowlist_only", True):
            allowed_domains = self.outreach_config.get("allowed_domains", [])
            domain = email.split("@")[-1].lower()
            
            if domain not in allowed_domains:
                return False, f"Domain '{domain}' not in allowlist"
        
        # Check justification required
        if self.outreach_config.get("require_justification", True):
            if not justification or len(justification) < 10:
                return False, "Justification required (min 10 chars)"
        
        # Check blocked keywords
        blocked = self.outreach_config.get("blocked_keywords", [])
        email_lower = email.lower()
        for keyword in blocked:
            if keyword in email_lower:
                return False, f"Email contains blocked keyword"
        
        # Check for duplicates (don't email same person twice)
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM outreach_log WHERE email = ?",
            (email,)
        )
        if cursor.fetchone()[0] > 0:
            conn.close()
            return False, "Email already contacted"
        
        conn.close()
        return True, "Approved"
    
    def log_outreach_attempt(self, email: str, justification: str, 
                            status: str, template: str = "default"):
        """Log outreach attempt for audit."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        domain = email.split("@")[-1].lower()
        
        cursor.execute("""
            INSERT INTO outreach_log (email, domain, justification, status, template_used)
            VALUES (?, ?, ?, ?, ?)
        """, (email, domain, justification, status, template))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Outreach logged: {email} - {status}")
    
    def add_to_allowlist(self, domain: str):
        """Add domain to allowlist."""
        self.config["outreach"]["allowed_domains"] = \
            self.config["outreach"].get("allowed_domains", []) + [domain]
        
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        logger.info(f"Added {domain} to allowlist")
    
    def get_outreach_stats(self) -> Dict:
        """Get outreach statistics."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Total sent
        cursor.execute("SELECT COUNT(*) FROM outreach_log")
        total = cursor.fetchone()[0]
        
        # Today's sends
        cursor.execute("""
            SELECT COUNT(*) FROM outreach_log 
            WHERE date(sent_at) = date('now')
        """)
        today = cursor.fetchone()[0]
        
        # Replies received
        cursor.execute("""
            SELECT COUNT(*) FROM outreach_log WHERE status = 'replied'
        """)
        replies = cursor.fetchone()[0]
        
        # Response rate
        response_rate = (replies / total * 100) if total > 0 else 0
        
        conn.close()
        
        return {
            "total_sent": total,
            "sent_today": today,
            "daily_limit": self.outreach_config.get("max_daily_sends", 5),
            "replies": replies,
            "response_rate": round(response_rate, 1)
        }

if __name__ == "__main__":
    outreach = SafeOutreach()
    
    print("Outreach Status:")
    print(f"Enabled: {outreach.is_outreach_enabled()}")
    print(f"Daily sends: {outreach.get_daily_send_count()}")
    print(f"Stats: {outreach.get_outreach_stats()}")
    
    # Test approval
    test_email = "test@example.com"
    test_justification = "Housing advocate working on rent control issues"
    
    approved, reason = outreach.can_send_outreach(test_email, test_justification)
    print(f"\nTest: {test_email}")
    print(f"Approved: {approved}")
    print(f"Reason: {reason}")
