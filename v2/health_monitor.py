#!/usr/bin/env python3
"""
V2 Health Monitoring - Source reliability tracking
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "v2_health.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "v2" / "la_agenda_v2.db"

class HealthMonitor:
    """Monitor system and source health."""
    
    def __init__(self):
        self.threshold = 0.8  # 80% success rate threshold
    
    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def record_source_check(self, source_id: str, success: bool, 
                           response_time_ms: int = 0, error: str = None):
        """Record a source check result."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        if success:
            cursor.execute("""
                UPDATE source_health 
                SET last_check = ?, last_success = ?, success_count = success_count + 1,
                    failure_count = 0, status = 'healthy', avg_response_time_ms = ?,
                    last_error = NULL
                WHERE source_id = ?
            """, (now, now, response_time_ms, source_id))
        else:
            cursor.execute("""
                UPDATE source_health 
                SET last_check = ?, failure_count = failure_count + 1,
                    last_error = ?, status = 
                    CASE 
                        WHEN failure_count >= 2 THEN 'down'
                        WHEN failure_count >= 1 THEN 'degraded'
                        ELSE 'healthy'
                    END
                WHERE source_id = ?
            """, (now, error, source_id))
        
        # Update success rate
        cursor.execute("""
            UPDATE source_health 
            SET success_rate = CAST(success_count AS REAL) / (success_count + failure_count)
            WHERE source_id = ?
        """, (source_id,))
        
        conn.commit()
        conn.close()
        
        status = "✅" if success else "❌"
        logger.info(f"{status} Source {source_id}: {'OK' if success else error}")
    
    def get_source_health(self) -> List[Dict]:
        """Get health status for all sources."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_id, name, last_check, last_success, 
                   success_rate, status, last_error
            FROM source_health
            ORDER BY success_rate ASC
        """)
        
        sources = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return sources
    
    def get_system_status(self) -> Dict:
        """Get overall system status for public page."""
        sources = self.get_source_health()
        
        healthy_count = sum(1 for s in sources if s["status"] == "healthy")
        degraded_count = sum(1 for s in sources if s["status"] == "degraded")
        down_count = sum(1 for s in sources if s["status"] == "down")
        
        overall_status = "operational"
        if down_count > 0:
            overall_status = "degraded"
        if down_count > len(sources) / 2:
            overall_status = "major_outage"
        
        return {
            "status": overall_status,
            "sources_total": len(sources),
            "healthy": healthy_count,
            "degraded": degraded_count,
            "down": down_count,
            "sources": sources,
            "updated_at": datetime.now().isoformat()
        }
    
    def log_system_event(self, event_type: str, component: str, 
                        message: str, details: str = None):
        """Log a system event."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Auto-tag common errors
        auto_tagged = False
        if "pdf" in message.lower() and "parse" in message.lower():
            auto_tagged = True
        elif "timeout" in message.lower() or "connection" in message.lower():
            auto_tagged = True
        elif "404" in message or "403" in message:
            auto_tagged = True
        
        cursor.execute("""
            INSERT INTO system_events (event_type, component, message, details, auto_tagged)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, component, message, details, auto_tagged))
        
        conn.commit()
        conn.close()
        
        logger.info(f"System event: [{event_type}] {component}: {message}")
    
    def generate_weekly_digest(self) -> str:
        """Generate weekly health summary email."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Get alerts sent this week
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM alerts_sent WHERE sent_at > ?
        """, (week_ago,))
        alerts_sent = cursor.fetchone()[0]
        
        # Get error count
        cursor.execute("""
            SELECT COUNT(*) FROM system_events 
            WHERE event_type = 'error' AND created_at > ?
        """, (week_ago,))
        error_count = cursor.fetchone()[0]
        
        # Get source issues
        cursor.execute("""
            SELECT source_id, status, last_error FROM source_health 
            WHERE status != 'healthy'
        """)
        issues = cursor.fetchall()
        
        conn.close()
        
        # Build digest
        digest = f"""📊 LA Agenda Alerts - Weekly Health Report

Week of {datetime.now().strftime("%Y-%m-%d")}

ALERTS SENT: {alerts_sent}
ERRORS LOGGED: {error_count}

SOURCE STATUS:
"""
        
        if issues:
            for issue in issues:
                digest += f"⚠️ {issue['source_id']}: {issue['status']}"
                if issue['last_error']:
                    digest += f" - {issue['last_error'][:50]}..."
                digest += "\n"
        else:
            digest += "✅ All sources healthy\n"
        
        digest += """
View full status: https://maxnguyen.github.io/la-agenda-alerts/status
"""
        
        return digest

if __name__ == "__main__":
    monitor = HealthMonitor()
    
    print("System Status:")
    status = monitor.get_system_status()
    print(f"Overall: {status['status']}")
    print(f"Healthy: {status['healthy']}/{status['sources_total']}")
    
    print("\nWeekly Digest:")
    print(monitor.generate_weekly_digest())
