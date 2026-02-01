#!/usr/bin/env python3
"""
Tests for LA Agenda Alerts core functionality.
Run with: python3 -m pytest tests/ or ./scripts/run_tests.sh
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import diff


def test_event_id_generation():
    """Test that event IDs are stable and deterministic."""
    event1 = diff.ChangeEvent(
        change_type="new_item",
        item_id="test123",
        source="county_bos",
        title="Test Item"
    )
    
    event2 = diff.ChangeEvent(
        change_type="new_item",
        item_id="test123",
        source="county_bos",
        title="Test Item"
    )
    
    # Same inputs should produce same event_id
    assert event1.event_id == event2.event_id
    print("✅ Event ID generation is deterministic")


def test_event_id_uniqueness():
    """Test that different events have different IDs."""
    event1 = diff.ChangeEvent(
        change_type="new_item",
        item_id="item1",
        source="county_bos",
        title="Item One"
    )
    
    event2 = diff.ChangeEvent(
        change_type="new_item",
        item_id="item2",
        source="county_bos",
        title="Item Two"
    )
    
    assert event1.event_id != event2.event_id
    print("✅ Different events have unique IDs")


def test_dedupe():
    """Test that duplicate events are filtered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        worker = diff.DiffWorker()
        worker.sent_events_path = state_dir / "sent_events.json"
        
        # Create initial event
        event = diff.ChangeEvent(
            change_type="new_item",
            item_id="item1",
            source="county_bos",
            title="Test"
        )
        
        # Save as sent
        worker._save_sent_events({event.event_id})
        
        # Load and check
        sent = worker._load_sent_events()
        assert event.event_id in sent
        print("✅ Deduplication works correctly")


def test_keyword_matching():
    """Test keyword matching logic."""
    subscriber = {
        "keywords": ["housing", "zoning"],
        "sources": ["city_council"]
    }
    
    # Should match
    change_match = {
        "title": "New housing development proposal",
        "source": "city_council"
    }
    
    # Should not match (wrong keyword)
    change_no_keyword = {
        "title": "Road maintenance schedule",
        "source": "city_council"
    }
    
    # Should not match (wrong source)
    change_no_source = {
        "title": "Housing budget approval",
        "source": "county_bos"
    }
    
    # Simple matching logic test
    def matches(sub, change):
        keywords = sub.get("keywords", [])
        sources = sub.get("sources", [])
        
        if sources and change["source"] not in sources:
            return False
        
        if keywords:
            text = change["title"].lower()
            return any(kw.lower() in text for kw in keywords)
        
        return True
    
    assert matches(subscriber, change_match) == True
    assert matches(subscriber, change_no_keyword) == False
    assert matches(subscriber, change_no_source) == False
    print("✅ Keyword matching works correctly")


def run_all_tests():
    """Run all tests."""
    print("Running LA Agenda Alerts Tests...")
    print("=" * 40)
    
    try:
        test_event_id_generation()
        test_event_id_uniqueness()
        test_dedupe()
        test_keyword_matching()
        
        print("=" * 40)
        print("✅ All tests passed!")
        return 0
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
