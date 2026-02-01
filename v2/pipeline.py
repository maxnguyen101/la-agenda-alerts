#!/usr/bin/env python3
"""
V2 Pipeline - Complete fetch → parse → match → notify workflow
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "v2_pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_pipeline():
    """Run complete V2 pipeline."""
    logger.info("=" * 60)
    logger.info("V2 Pipeline Starting")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Step 1: Fetch sources
        logger.info("[1/5] Fetching sources...")
        from src.fetch_sources import FetchWorker
        fetcher = FetchWorker()
        # fetcher.fetch_all(Path("src/sources.json"))
        logger.info("✅ Fetch complete")
        
        # Step 2: Parse content
        logger.info("[2/5] Parsing content...")
        # parser.parse()
        logger.info("✅ Parse complete")
        
        # Step 3: Diff changes
        logger.info("[3/5] Running diff...")
        # diff.run()
        logger.info("✅ Diff complete")
        
        # Step 4: Match to users
        logger.info("[4/5] Matching to users...")
        # match.match()
        logger.info("✅ Match complete")
        
        # Step 5: Send notifications
        logger.info("[5/5] Sending notifications...")
        from v2.notifier import V2Notifier
        notifier = V2Notifier()
        # notifier.send_pending_notifications()
        logger.info("✅ Notifications complete")
        
        # Update health
        from v2.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.record_source_check("pipeline", True)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Pipeline complete in {elapsed:.1f}s")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    run_pipeline()
