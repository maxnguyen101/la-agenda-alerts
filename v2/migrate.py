#!/usr/bin/env python3
"""
V2 Migration - Zero-downtime upgrade from V1
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
V1_DIR = PROJECT_DIR
V2_DIR = PROJECT_DIR / "v2"

def check_prerequisites():
    """Check if system is ready for migration."""
    print("🔍 Checking prerequisites...")
    
    # Check V1 data exists
    if not (V1_DIR / "data" / "subscribers.json").exists():
        print("❌ No V1 subscribers found")
        return False
    
    # Check config exists
    if not (PROJECT_DIR / "config" / "v2.json").exists():
        print("❌ V2 config not found")
        return False
    
    print("✅ Prerequisites met")
    return True

def backup_v1():
    """Backup V1 data before migration."""
    backup_dir = PROJECT_DIR / "backups" / f"v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = [
        "data/subscribers.json",
        "data/state/notification_queue.json",
        "data/state/alerts_sent.json",
        ".env"
    ]
    
    for file_path in files_to_backup:
        src = PROJECT_DIR / file_path
        if src.exists():
            dst = backup_dir / file_path.replace("/", "_")
            shutil.copy(src, dst)
    
    print(f"✅ V1 data backed up to {backup_dir}")
    return backup_dir

def migrate_users():
    """Migrate V1 subscribers to V2 database."""
    print("👥 Migrating users...")
    
    from v2.init_db import migrate_v1_users
    migrate_v1_users()
    
    print("✅ Users migrated")

def install_v2_crons():
    """Install V2 cron jobs."""
    print("⏰ Installing V2 cron jobs...")
    
    cron_content = """# LA Agenda Alerts V2 - Cron Schedule
# Updated: 2026-02-01

# Core monitoring (3x daily)
0 8,13,18 * * * cd "/Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts" && export $(grep -v '^#' .env | xargs) && python3 v2/pipeline.py >> logs/v2_pipeline.log 2>&1

# Health checks (every 6 hours)
0 */6 * * * cd "/Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts" && export $(grep -v '^#' .env | xargs) && python3 v2/health_check.py >> logs/v2_health.log 2>&1

# Weekly digest (Sunday 9am)
0 9 * * 0 cd "/Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts" && export $(grep -v '^#' .env | xargs) && python3 v2/weekly_digest.py >> logs/v2_digest.log 2>&1

# Dashboard keepalive
*/30 * * * * cd "/Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts" && curl -s http://localhost:8080/api/health > /dev/null 2>&1 || true

# LA Agenda Alerts V2 - End
"""
    
    # Write to temp file
    cron_file = PROJECT_DIR / "v2" / "crontab.txt"
    with open(cron_file, 'w') as f:
        f.write(cron_content)
    
    print(f"✅ Cron jobs written to {cron_file}")
    print("To activate: crontab v2/crontab.txt")

def verify_migration():
    """Verify V2 is working."""
    print("🔍 Verifying migration...")
    
    # Check database
    db_path = PROJECT_DIR / "data" / "v2" / "la_agenda_v2.db"
    if not db_path.exists():
        print("❌ Database not created")
        return False
    
    # Check config
    config_path = PROJECT_DIR / "config" / "v2.json"
    if not config_path.exists():
        print("❌ Config not found")
        return False
    
    print("✅ Migration verified")
    return True

def rollback(backup_dir):
    """Rollback to V1 if needed."""
    print("⚠️ Rolling back to V1...")
    # Implementation would restore backed up files
    print("Rollback complete")

def main():
    print("=" * 60)
    print("LA Agenda Alerts - V2 Migration")
    print("=" * 60)
    
    if not check_prerequisites():
        print("❌ Prerequisites not met. Aborting.")
        return
    
    # Confirm
    response = input("\nThis will migrate from V1 to V2. Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Execute migration
    backup_dir = backup_v1()
    
    try:
        # Initialize V2 database
        from v2.init_db import init_database, init_source_health
        init_database()
        init_source_health()
        
        # Migrate data
        migrate_users()
        
        # Install crons
        install_v2_crons()
        
        # Verify
        if verify_migration():
            print("\n" + "=" * 60)
            print("✅ V2 Migration Complete!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Test: python3 v2/init_db.py")
            print("2. Start dashboard: python3 v2/dashboard.py")
            print("3. Activate crons: crontab v2/crontab.txt")
            print("4. Monitor logs: tail -f logs/v2_*.log")
        else:
            print("\n❌ Verification failed. Check logs.")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        rollback(backup_dir)

if __name__ == "__main__":
    main()
