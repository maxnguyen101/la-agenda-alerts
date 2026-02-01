#!/usr/bin/env python3
"""
V2 Authentication - Magic Link System
No passwords, secure, Pro+ only
"""

import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

DB_PATH = Path(__file__).parent.parent / "data" / "v2" / "la_agenda_v2.db"

def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_magic_link(email: str) -> Optional[str]:
    """Generate a magic link token for user login."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists and requires login
    cursor.execute("SELECT id, plan FROM users WHERE email = ? AND status = 'active'", (email,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    # Free users don't need login
    if user["plan"] == "free":
        conn.close()
        return "FREE_TIER_NO_LOGIN_REQUIRED"
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=1)
    
    cursor.execute("""
        UPDATE users 
        SET magic_link_token = ?, magic_link_expires = ?
        WHERE id = ?
    """, (token, expires.isoformat(), user["id"]))
    
    conn.commit()
    conn.close()
    
    # Return full magic link URL
    return f"https://maxnguyen.github.io/la-agenda-alerts/login?token={token}"

def validate_token(token: str) -> Optional[Dict]:
    """Validate a magic link token."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, email, plan, magic_link_expires 
        FROM users 
        WHERE magic_link_token = ? AND status = 'active'
    """, (token,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    # Check expiration
    expires = datetime.fromisoformat(user["magic_link_expires"])
    if datetime.now() > expires:
        conn.close()
        return None
    
    # Update last login and clear token
    cursor.execute("""
        UPDATE users 
        SET last_login = ?, magic_link_token = NULL, magic_link_expires = NULL
        WHERE id = ?
    """, (datetime.now().isoformat(), user["id"]))
    
    conn.commit()
    conn.close()
    
    return {
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"]
    }

def check_auth_required(email: str) -> bool:
    """Check if user requires authentication."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT plan FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return False  # New users default to free
    
    return user["plan"] in ("pro", "org")

def get_user_plan(email: str) -> str:
    """Get user's plan tier."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT plan FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    return user["plan"] if user else "free"

def can_access_feature(email: str, feature: str, config: Dict) -> bool:
    """Check if user can access a feature based on plan."""
    plan = get_user_plan(email)
    plan_config = config.get("plans", {}).get(plan, {})
    
    feature_map = {
        "sms": "sms" in plan_config.get("channels", []),
        "calendar_ics": plan != "free",
        "advanced_keywords": plan_config.get("keyword_logic") == "advanced",
        "team_features": plan_config.get("team_features", False),
        "priority_support": plan_config.get("support_level") == "priority"
    }
    
    return feature_map.get(feature, False)

if __name__ == "__main__":
    # Test
    print("Testing auth system...")
    
    # Create test pro user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (id, email, plan, status)
        VALUES ('test123', 'test@example.com', 'pro', 'active')
    """)
    conn.commit()
    conn.close()
    
    link = generate_magic_link("test@example.com")
    print(f"Magic link: {link}")
    
    print(f"Auth required for pro: {check_auth_required('test@example.com')}")
