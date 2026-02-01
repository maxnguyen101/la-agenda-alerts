#!/usr/bin/env python3
"""
V2 Database Setup - SQLite with WAL mode for reliability
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "v2"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "la_agenda_v2.db"

def init_database():
    """Initialize SQLite database with all V2 tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            plan TEXT CHECK(plan IN ('free', 'pro', 'org')) DEFAULT 'free',
            status TEXT CHECK(status IN ('active', 'paused', 'cancelled')) DEFAULT 'active',
            billing_status TEXT DEFAULT 'trial',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            magic_link_token TEXT,
            magic_link_expires TIMESTAMP
        )
    """)
    
    # User preferences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id TEXT PRIMARY KEY,
            keywords TEXT DEFAULT '[]',
            keyword_logic TEXT DEFAULT 'OR',
            sources TEXT DEFAULT '["city_council", "county_bos", "plum_committee"]',
            frequency TEXT DEFAULT 'instant',
            sms_number TEXT,
            timezone TEXT DEFAULT 'America/Los_Angeles',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Alert history with retry tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts_sent (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            change_type TEXT NOT NULL,
            title TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            channel TEXT CHECK(channel IN ('email', 'sms')) DEFAULT 'email',
            status TEXT CHECK(status IN ('sent', 'failed', 'retrying', 'delivered')) DEFAULT 'sent',
            retry_count INTEGER DEFAULT 0,
            error_message TEXT
        )
    """)
    
    # Source health tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_health (
            source_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            last_check TIMESTAMP,
            last_success TIMESTAMP,
            failure_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            avg_response_time_ms INTEGER,
            status TEXT CHECK(status IN ('healthy', 'degraded', 'down')) DEFAULT 'healthy',
            last_error TEXT
        )
    """)
    
    # Outreach audit log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            domain TEXT NOT NULL,
            justification TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('sent', 'failed', 'bounced', 'replied')),
            template_used TEXT
        )
    """)
    
    # System events (errors, warnings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT CHECK(event_type IN ('error', 'warning', 'info')),
            component TEXT,
            message TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_tagged BOOLEAN DEFAULT 0
        )
    """)
    
    # Billing/events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT CHECK(event_type IN ('trial_start', 'payment_success', 'payment_failed', 'cancelled')),
            amount_cents INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ V2 Database initialized: {DB_PATH}")

def migrate_v1_users():
    """Migrate existing subscribers from V1."""
    v1_subscribers = Path(__file__).parent.parent / "data" / "subscribers.json"
    
    if not v1_subscribers.exists():
        print("⚠️ No V1 subscribers to migrate")
        return
    
    with open(v1_subscribers) as f:
        data = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    migrated = 0
    for sub in data.get("subscribers", []):
        try:
            import uuid
            user_id = str(uuid.uuid4())[:8]
            
            cursor.execute("""
                INSERT OR IGNORE INTO users (id, email, plan, status)
                VALUES (?, ?, 'free', 'active')
            """, (user_id, sub["email"]))
            
            cursor.execute("""
                INSERT OR IGNORE INTO preferences (user_id, keywords, sources, frequency)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                json.dumps(sub.get("keywords", [])),
                json.dumps(sub.get("sources", ["city_council", "county_bos", "plum_committee"])),
                sub.get("frequency", "instant")
            ))
            
            migrated += 1
        except Exception as e:
            print(f"⚠️ Failed to migrate {sub.get('email')}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Migrated {migrated} V1 subscribers")

def init_source_health():
    """Initialize source health tracking."""
    sources_path = Path(__file__).parent.parent / "src" / "sources.json"
    
    if not sources_path.exists():
        print("⚠️ No sources.json found")
        return
    
    with open(sources_path) as f:
        data = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for source in data.get("sources", []):
        cursor.execute("""
            INSERT OR IGNORE INTO source_health (source_id, name, status)
            VALUES (?, ?, 'healthy')
        """, (source["id"], source["name"]))
    
    conn.commit()
    conn.close()
    print(f"✅ Initialized {len(data.get('sources', []))} source health trackers")

if __name__ == "__main__":
    init_database()
    migrate_v1_users()
    init_source_health()
    print("\n🎉 V2 Database ready!")
