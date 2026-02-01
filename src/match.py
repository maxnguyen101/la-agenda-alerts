#!/usr/bin/env python3
"""
Match worker: Matches changes to subscriber preferences.
Outputs notification_queue.json
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
STATE_DIR = DATA_DIR / "state"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "match.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MatchWorker:
    """Matches changes to subscriber interests."""
    
    def __init__(self):
        self.subscribers_path = DATA_DIR / "subscribers.json"
        self.changes_path = STATE_DIR / "changes.json"
        self.queue_path = STATE_DIR / "notification_queue.json"
    
    def match(self) -> List[Dict]:
        """Match changes to subscribers and build notification queue."""
        
        # Load subscribers
        if not self.subscribers_path.exists():
            logger.error("No subscribers.json found")
            return []
        
        with open(self.subscribers_path) as f:
            subscribers = json.load(f)["subscribers"]
        
        # Load changes
        if not self.changes_path.exists():
            logger.info("No changes to match")
            return []
        
        with open(self.changes_path) as f:
            changes = json.load(f)
        
        # Build notification queue
        queue = []
        
        for subscriber in subscribers:
            if subscriber.get("status") != "active":
                continue
            
            matched = self._match_subscriber(subscriber, changes)
            
            for change in matched:
                notification = {
                    "notification_id": f"{subscriber['id']}:{change['event_id']}",
                    "subscriber_id": subscriber["id"],
                    "email": subscriber["email"],
                    "change": change,
                    "frequency": subscriber.get("frequency", "instant"),
                    "created_at": datetime.now().isoformat(),
                    "status": "pending"
                }
                queue.append(notification)
        
        # Save queue
        with open(self.queue_path, 'w') as f:
            json.dump(queue, f, indent=2)
        
        logger.info(f"Match complete: {len(queue)} notifications queued")
        return queue
    
    def _match_subscriber(self, subscriber: Dict, changes: List[Dict]) -> List[Dict]:
        """Match changes to a single subscriber."""
        matched = []
        
        keywords = subscriber.get("keywords", [])
        sources = subscriber.get("sources", [])
        
        for change in changes:
            # Source filter
            if sources and change["source"] not in sources:
                continue
            
            # Keyword filter
            if keywords:
                text_to_match = change["title"].lower()
                if change.get("attachment"):
                    text_to_match += " " + change["attachment"].get("name", "").lower()
                
                keyword_match = False
                for keyword in keywords:
                    if keyword.lower() in text_to_match:
                        keyword_match = True
                        break
                
                if not keyword_match:
                    continue
            
            matched.append(change)
        
        return matched


def main():
    """Main entry point."""
    worker = MatchWorker()
    queue = worker.match()
    
    # Print summary
    by_subscriber = {}
    for notif in queue:
        sub_id = notif["subscriber_id"]
        by_subscriber[sub_id] = by_subscriber.get(sub_id, 0) + 1
    
    logger.info("Notifications by subscriber:")
    for sub_id, count in by_subscriber.items():
        logger.info(f"  {sub_id}: {count}")
    
    print(json.dumps(queue, indent=2))


if __name__ == "__main__":
    main()
