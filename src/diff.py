#!/usr/bin/env python3
"""
Diff worker: Compares current_items.json to last_items.json.
Outputs changes to data/state/changes.json
"""

import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

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
        logging.FileHandler(LOGS_DIR / "diff.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ChangeEvent:
    """Represents a detected change."""
    
    def __init__(self,
                 change_type: str,
                 item_id: str,
                 source: str,
                 title: str,
                 meeting_datetime: Optional[str] = None,
                 attachment: Optional[Dict] = None,
                 source_url: Optional[str] = None):
        self.change_type = change_type
        self.item_id = item_id
        self.source = source
        self.title = title
        self.meeting_datetime = meeting_datetime
        self.attachment = attachment
        self.source_url = source_url
        self.event_id = self._generate_event_id()
        self.detected_at = datetime.now().isoformat()
    
    def _generate_event_id(self) -> str:
        """Generate stable event ID for deduplication."""
        content = f"{self.change_type}:{self.item_id}:{self.title}"
        if self.attachment:
            content += f":{self.attachment.get('url', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "change_type": self.change_type,
            "item_id": self.item_id,
            "source": self.source,
            "title": self.title,
            "meeting_datetime": self.meeting_datetime,
            "attachment": self.attachment,
            "source_url": self.source_url,
            "detected_at": self.detected_at
        }


class DiffWorker:
    """Compares current state to last state and generates change events."""
    
    def __init__(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.current_path = STATE_DIR / "current_items.json"
        self.last_path = STATE_DIR / "last_items.json"
        self.changes_path = STATE_DIR / "changes.json"
        self.sent_events_path = STATE_DIR / "sent_events.json"
    
    def diff(self) -> List[Dict]:
        """Compare current to last and return changes."""
        
        # Load current items
        if not self.current_path.exists():
            logger.error("No current_items.json found")
            return []
        
        with open(self.current_path) as f:
            current_items = json.load(f)
        
        # Load last items (empty if first run)
        last_items = []
        if self.last_path.exists():
            with open(self.last_path) as f:
                last_items = json.load(f)
        
        # Load already sent events for deduplication
        sent_events = self._load_sent_events()
        
        # Build lookup maps
        last_map = {item["item_id"]: item for item in last_items}
        current_map = {item["item_id"]: item for item in current_items}
        
        changes = []
        
        # Find new items
        for item_id, item in current_map.items():
            if item_id not in last_map:
                event = ChangeEvent(
                    change_type="new_item",
                    item_id=item_id,
                    source=item["source"],
                    title=item["title"],
                    meeting_datetime=item.get("meeting_datetime"),
                    source_url=item.get("source_url")
                )
                if event.event_id not in sent_events:
                    changes.append(event.to_dict())
                    sent_events.add(event.event_id)
            else:
                # Check for changes in existing items
                last_item = last_map[item_id]
                item_changes = self._detect_item_changes(last_item, item)
                
                for change in item_changes:
                    if change.event_id not in sent_events:
                        changes.append(change.to_dict())
                        sent_events.add(change.event_id)
        
        # Find removed items
        for item_id, item in last_map.items():
            if item_id not in current_map:
                event = ChangeEvent(
                    change_type="removed_item",
                    item_id=item_id,
                    source=item["source"],
                    title=item["title"],
                    meeting_datetime=item.get("meeting_datetime"),
                    source_url=item.get("source_url")
                )
                if event.event_id not in sent_events:
                    changes.append(event.to_dict())
                    sent_events.add(event.event_id)
        
        # Save changes
        with open(self.changes_path, 'w') as f:
            json.dump(changes, f, indent=2)
        
        # Save sent events
        self._save_sent_events(sent_events)
        
        logger.info(f"Diff complete: {len(changes)} changes detected")
        return changes
    
    def _detect_item_changes(self, old: Dict, new: Dict) -> List[ChangeEvent]:
        """Detect changes within an existing item."""
        changes = []
        
        # Check meeting time change
        old_time = old.get("meeting_datetime")
        new_time = new.get("meeting_datetime")
        if old_time != new_time and new_time is not None:
            changes.append(ChangeEvent(
                change_type="meeting_time_changed",
                item_id=new["item_id"],
                source=new["source"],
                title=new["title"],
                meeting_datetime=new_time,
                source_url=new.get("source_url")
            ))
        
        # Check attachment changes
        old_attachments = {a.get("url", ""): a for a in old.get("attachments", [])}
        new_attachments = {a.get("url", ""): a for a in new.get("attachments", [])}
        
        # New attachments
        for url, attachment in new_attachments.items():
            if url not in old_attachments:
                changes.append(ChangeEvent(
                    change_type="attachment_added",
                    item_id=new["item_id"],
                    source=new["source"],
                    title=new["title"],
                    meeting_datetime=new.get("meeting_datetime"),
                    attachment=attachment,
                    source_url=new.get("source_url")
                ))
        
        # Changed attachments
        for url, new_attach in new_attachments.items():
            if url in old_attachments:
                old_attach = old_attachments[url]
                if new_attach.get("sha256") != old_attach.get("sha256"):
                    changes.append(ChangeEvent(
                        change_type="attachment_changed",
                        item_id=new["item_id"],
                        source=new["source"],
                        title=new["title"],
                        meeting_datetime=new.get("meeting_datetime"),
                        attachment=new_attach,
                        source_url=new.get("source_url")
                    ))
        
        return changes
    
    def _load_sent_events(self) -> Set[str]:
        """Load set of already sent event IDs."""
        if not self.sent_events_path.exists():
            return set()
        
        try:
            with open(self.sent_events_path) as f:
                return set(json.load(f))
        except:
            return set()
    
    def _save_sent_events(self, events: Set[str]):
        """Save set of sent event IDs."""
        with open(self.sent_events_path, 'w') as f:
            json.dump(list(events), f)
    
    def update_last_state(self):
        """Copy current_items.json to last_items.json after successful notify."""
        if self.current_path.exists():
            import shutil
            shutil.copy(self.current_path, self.last_path)
            logger.info("Updated last_items.json")


def main():
    """Main entry point."""
    worker = DiffWorker()
    changes = worker.diff()
    
    # Print summary
    by_type = {}
    for change in changes:
        change_type = change["change_type"]
        by_type[change_type] = by_type.get(change_type, 0) + 1
    
    logger.info(f"Changes by type:")
    for change_type, count in by_type.items():
        logger.info(f"  {change_type}: {count}")
    
    print(json.dumps(changes, indent=2))


if __name__ == "__main__":
    main()
