#!/usr/bin/env python3
"""
Production Diff - Smart change detection with noise filtering
"""

import difflib
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class ChangeSummary:
    """Summary of changes between two documents."""
    changed: bool
    fingerprint_changed: bool
    added_lines: List[str]
    removed_lines: List[str]
    percent_changed: float
    noise_only: bool  # True if only noise (timestamps, etc) changed
    old_fingerprint: str
    new_fingerprint: str


class ProductionDiff:
    """Smart diff that ignores noise and produces clean summaries."""
    
    # Patterns to ignore as noise
    NOISE_PATTERNS = [
        r'(?i)printed?\s+(on|at)\s*:?\s*\d',  # Printed on/at dates
        r'(?i)page\s+\d+\s+of\s+\d+',  # Page numbers
        r'(?i)updated?\s*:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Update timestamps
        r'(?i)last\s+modified\s*:?\s*',  # Last modified
        r'(?i)generated\s+(on|at)\s*:?\s*\d',  # Generated dates
        r'^\s*\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\s*$',  # Bare timestamps
        r'^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$',  # Bare dates
    ]
    
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.fingerprints_file = state_dir / 'fingerprints.json'
        self.fingerprints = self._load_fingerprints()
    
    def _load_fingerprints(self) -> dict:
        """Load stored fingerprints."""
        if self.fingerprints_file.exists():
            try:
                with open(self.fingerprints_file) as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_fingerprints(self):
        """Save fingerprints to disk."""
        with open(self.fingerprints_file, 'w') as f:
            json.dump(self.fingerprints, f, indent=2)
    
    def compare(self, source_id: str, new_text: str, new_fingerprint: str) -> ChangeSummary:
        """
        Compare new text against last known version.
        
        Returns ChangeSummary with detailed change information.
        """
        old_fingerprint = self.fingerprints.get(source_id, {}).get('fingerprint', '')
        old_text = self.fingerprints.get(source_id, {}).get('text', '')
        
        # Quick check: if fingerprint unchanged, no meaningful change
        if new_fingerprint == old_fingerprint:
            return ChangeSummary(
                changed=False,
                fingerprint_changed=False,
                added_lines=[],
                removed_lines=[],
                percent_changed=0.0,
                noise_only=False,
                old_fingerprint=old_fingerprint,
                new_fingerprint=new_fingerprint
            )
        
        # Fingerprint changed, do detailed diff
        added, removed = self._compute_diff(old_text, new_text)
        
        # Check if it's only noise
        noise_only = self._is_noise_only(added, removed)
        
        # Calculate percent changed
        percent = self._calculate_percent_changed(old_text, new_text)
        
        # Store new fingerprint and text
        self.fingerprints[source_id] = {
            'fingerprint': new_fingerprint,
            'text': new_text[:5000],  # Store truncated for space
            'updated_at': datetime.now().isoformat()
        }
        self._save_fingerprints()
        
        return ChangeSummary(
            changed=not noise_only and (len(added) > 0 or len(removed) > 0),
            fingerprint_changed=True,
            added_lines=added[:20],  # Limit to top 20
            removed_lines=removed[:20],
            percent_changed=percent,
            noise_only=noise_only,
            old_fingerprint=old_fingerprint,
            new_fingerprint=new_fingerprint
        )
    
    def _compute_diff(self, old_text: str, new_text: str) -> Tuple[List[str], List[str]]:
        """Compute line-by-line diff."""
        old_lines = old_text.split('\n') if old_text else []
        new_lines = new_text.split('\n') if new_text else []
        
        # Use unified diff for cleaner results
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        
        added = []
        removed = []
        
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                content = line[1:].strip()
                if content and not self._is_noise_line(content):
                    added.append(content)
            elif line.startswith('-') and not line.startswith('---'):
                content = line[1:].strip()
                if content and not self._is_noise_line(content):
                    removed.append(content)
        
        return added, removed
    
    def _is_noise_line(self, line: str) -> bool:
        """Check if a line is just noise."""
        import re
        for pattern in self.NOISE_PATTERNS:
            if re.search(pattern, line):
                return True
        # Skip very short lines (likely artifacts)
        if len(line.strip()) < 3:
            return True
        return False
    
    def _is_noise_only(self, added: List[str], removed: List[str]) -> bool:
        """Check if all changes are just noise."""
        # If substantial non-noise lines changed, it's real
        substantial_added = [l for l in added if len(l) > 20]
        substantial_removed = [l for l in removed if len(l) > 20]
        
        # If only short/noise lines changed, probably just timestamps
        if not substantial_added and not substantial_removed:
            return True
        
        return False
    
    def _calculate_percent_changed(self, old_text: str, new_text: str) -> float:
        """Calculate rough percentage of text that changed."""
        if not old_text:
            return 100.0 if new_text else 0.0
        
        old_len = len(old_text)
        new_len = len(new_text)
        
        if old_len == 0:
            return 100.0
        
        # Simple heuristic based on length difference
        diff = abs(new_len - old_len)
        percent = (diff / old_len) * 100
        
        # Cap at 100%
        return min(100.0, percent)
    
    def get_last_text(self, source_id: str) -> Optional[str]:
        """Get last known text for a source."""
        return self.fingerprints.get(source_id, {}).get('text')
    
    def get_last_fingerprint(self, source_id: str) -> str:
        """Get last fingerprint for a source."""
        return self.fingerprints.get(source_id, {}).get('fingerprint', '')


if __name__ == '__main__':
    import logging
    import tempfile
    logging.basicConfig(level=logging.INFO)
    
    with tempfile.TemporaryDirectory() as tmp:
        differ = ProductionDiff(Path(tmp))
        
        # Test 1: No change
        result = differ.compare('test', 'Hello world', hashlib.sha256(b'Hello world').hexdigest())
        print(f"First run (new): changed={result.changed}, noise={result.noise_only}")
        
        # Test 2: Same content
        result = differ.compare('test', 'Hello world', hashlib.sha256(b'Hello world').hexdigest())
        print(f"Second run (same): changed={result.changed}")
        
        # Test 3: Real change
        result = differ.compare('test', 'Hello world! New agenda item added.', hashlib.sha256(b'Hello world! New agenda item added.').hexdigest())
        print(f"Third run (changed): changed={result.changed}, added={len(result.added_lines)}")
        
        # Test 4: Noise only (timestamp)
        old = "Agenda\nItem 1\nPrinted on 2024-01-15"
        new = "Agenda\nItem 1\nPrinted on 2024-01-16"
        differ.compare('test2', old, hashlib.sha256(old.encode()).hexdigest())
        result = differ.compare('test2', new, hashlib.sha256(new.encode()).hexdigest())
        print(f"Timestamp change: changed={result.changed}, noise={result.noise_only}")
