#!/usr/bin/env python3
"""
Parse worker: Extracts agenda items from fetched HTML/PDFs.
Outputs normalized items to data/state/current_items.json
"""

import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
STATE_DIR = DATA_DIR / "state"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "parse.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AgendaItem:
    """Normalized agenda item."""
    
    def __init__(self,
                 source: str,
                 title: str,
                 item_id: Optional[str] = None,
                 meeting_datetime: Optional[str] = None,
                 attachments: Optional[List[Dict]] = None,
                 source_url: Optional[str] = None):
        self.source = source
        self.title = title.strip()
        self.item_id = item_id or self._generate_id()
        self.meeting_datetime = meeting_datetime
        self.attachments = attachments or []
        self.source_url = source_url
        self.detected_at = datetime.now().isoformat()
    
    def _generate_id(self) -> str:
        """Generate stable ID from content."""
        content = f"{self.source}:{self.title}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "source": self.source,
            "title": self.title,
            "meeting_datetime": self.meeting_datetime,
            "attachments": self.attachments,
            "source_url": self.source_url,
            "detected_at": self.detected_at
        }


class ParseWorker:
    """Parses fetched content into normalized agenda items."""
    
    def __init__(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    def parse_latest(self) -> List[Dict]:
        """Parse the most recent fetch run."""
        # Find latest run directory
        runs = sorted(RAW_DIR.glob("*/*/"))
        if not runs:
            logger.error("No fetch runs found")
            return []
        
        latest_run = runs[-1]
        logger.info(f"Parsing run: {latest_run}")
        
        all_items = []
        
        # Process each source
        for source_dir in latest_run.iterdir():
            if source_dir.is_dir():
                items = self._parse_source(source_dir)
                all_items.extend(items)
        
        # Save to state
        output_path = STATE_DIR / "current_items.json"
        with open(output_path, 'w') as f:
            json.dump(all_items, f, indent=2)
        
        logger.info(f"Parsed {len(all_items)} items. Saved to {output_path}")
        return all_items
    
    def _parse_source(self, source_dir: Path) -> List[Dict]:
        """Parse a single source directory."""
        source_id = source_dir.name
        items = []
        
        # Find HTML files
        html_files = list(source_dir.glob("*.html"))
        
        for html_file in html_files:
            try:
                content = html_file.read_text(encoding='utf-8', errors='replace')
                parsed = self._extract_items(content, source_id)
                items.extend([item.to_dict() for item in parsed])
            except Exception as e:
                logger.error(f"Failed to parse {html_file}: {e}")
        
        return items
    
    def _extract_items(self, html: str, source: str) -> List[AgendaItem]:
        """Extract agenda items from HTML based on source type."""
        items = []
        
        if source == "county_bos":
            items = self._parse_county_bos(html)
        elif source == "city_council":
            items = self._parse_city_council(html)
        elif source == "plum_committee":
            items = self._parse_plum(html)
        
        return items
    
    def _parse_county_bos(self, html: str) -> List[AgendaItem]:
        """Parse LA County Board of Supervisors HTML."""
        items = []
        
        # Look for meeting/announcement sections
        # This is a basic implementation - would need refinement for production
        
        # Try to find meeting dates
        date_patterns = [
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}/\d{1,2}/\d{2,4}',
        ]
        
        meeting_date = None
        for pattern in date_patterns:
            match = re.search(pattern, html)
            if match:
                meeting_date = match.group(0)
                break
        
        # Look for PDF attachments in the HTML
        pdf_pattern = r'href=["\']([^"\']*\.pdf)["\'][^>]*>([^<]*)</a>'
        pdf_matches = re.findall(pdf_pattern, html, re.IGNORECASE)
        
        for url, text in pdf_matches:
            # Clean up URL
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://bos.lacounty.gov' + url
            
            item = AgendaItem(
                source="county_bos",
                title=text.strip() or "Agenda Document",
                meeting_datetime=meeting_date,
                attachments=[{
                    "name": text.strip() or "document.pdf",
                    "url": url,
                    "type": "pdf"
                }],
                source_url=url
            )
            items.append(item)
        
        # If no PDFs found, create a generic item
        if not items:
            items.append(AgendaItem(
                source="county_bos",
                title="Board of Supervisors Page",
                meeting_datetime=meeting_date,
                source_url="https://bos.lacounty.gov/"
            ))
        
        return items
    
    def _parse_city_council(self, html: str) -> List[AgendaItem]:
        """Parse LA City Council HTML."""
        items = []
        
        # Look for council file references
        cf_pattern = r'CF\s*\d{2}-\d{4}'
        cf_matches = re.findall(cf_pattern, html)
        
        for cf in cf_matches:
            item = AgendaItem(
                source="city_council",
                title=f"Council File {cf}",
                item_id=f"cc_{cf.replace(' ', '_')}",
                source_url="https://lacity.gov/about/about-city-government/city-council"
            )
            items.append(item)
        
        if not items:
            items.append(AgendaItem(
                source="city_council",
                title="City Council Page",
                source_url="https://lacity.gov/about/about-city-government/city-council"
            ))
        
        return items
    
    def _parse_plum(self, html: str) -> List[AgendaItem]:
        """Parse PLUM Committee HTML."""
        items = []
        
        # Similar to city council but for PLUM
        items.append(AgendaItem(
            source="plum_committee",
            title="PLUM Committee Page",
            source_url="https://lacity.gov/about/about-city-government/city-council/committees/planning-and-land-use-management-committee"
        ))
        
        return items


def main():
    """Main entry point."""
    worker = ParseWorker()
    items = worker.parse_latest()
    
    # Print summary
    by_source = {}
    for item in items:
        source = item["source"]
        by_source[source] = by_source.get(source, 0) + 1
    
    logger.info(f"Parse complete: {len(items)} total items")
    for source, count in by_source.items():
        logger.info(f"  {source}: {count} items")
    
    print(json.dumps(items, indent=2))


if __name__ == "__main__":
    main()
