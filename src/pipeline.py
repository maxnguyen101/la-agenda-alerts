#!/usr/bin/env python3
"""
Production Pipeline - Complete fetch → parse → diff → match → notify workflow
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ProductionPipeline:
    """End-to-end production pipeline for LA Agenda Alerts."""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.parent
        self.cache_dir = self.project_dir / "data" / "cache"
        self.state_dir = self.project_dir / "data" / "state"
        self.sources_file = self.project_dir / "src" / "sources.json"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Import production modules
        from src.fetcher import ProductionFetcher
        from src.parser import ProductionParser
        from src.diff import ProductionDiff
        
        self.fetcher = ProductionFetcher(self.cache_dir)
        self.parser = ProductionParser()
        self.differ = ProductionDiff(self.state_dir)
        
        self.results = {
            'started_at': datetime.now().isoformat(),
            'sources_checked': 0,
            'sources_failed': 0,
            'changes_detected': 0,
            'alerts_sent': 0,
            'errors': []
        }
    
    def run(self):
        """Run complete pipeline."""
        logger.info("=" * 60)
        logger.info("PRODUCTION PIPELINE STARTING")
        logger.info("=" * 60)
        
        try:
            # Load sources
            sources = self._load_sources()
            logger.info(f"Loaded {len(sources)} sources")
            
            # Process each source
            for source in sources:
                try:
                    self._process_source(source)
                except Exception as e:
                    logger.error(f"Failed to process {source['id']}: {e}")
                    self.results['sources_failed'] += 1
                    self.results['errors'].append(f"{source['id']}: {str(e)}")
            
            # Clean old cache
            self.fetcher.clean_old_cache(max_age_days=7)
            
            # Summary
            self.results['ended_at'] = datetime.now().isoformat()
            self._log_summary()
            
            return 0 if self.results['sources_failed'] == 0 else 1
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return 1
    
    def _load_sources(self) -> list:
        """Load sources configuration."""
        with open(self.sources_file) as f:
            return json.load(f).get('sources', [])
    
    def _process_source(self, source: dict):
        """Process a single source."""
        source_id = source['id']
        urls = source.get('urls', [])
        
        logger.info(f"Processing {source_id}...")
        self.results['sources_checked'] += 1
        
        # Fetch each URL for this source
        all_texts = []
        for url in urls:
            content, metadata = self.fetcher.fetch(url, source_id)
            
            if content is None:
                logger.warning(f"Failed to fetch {url}: {metadata.get('error')}")
                continue
            
            # Parse content
            parsed = self.parser.parse(
                content, 
                metadata.get('content_type', 'unknown'),
                url,
                source_id
            )
            
            if not self.parser.is_valid_parse(parsed):
                logger.warning(f"Low confidence parse for {source_id}: {parsed.confidence}")
                if parsed.parse_warnings:
                    logger.warning(f"Warnings: {parsed.parse_warnings}")
                continue
            
            all_texts.append(parsed.text)
        
        if not all_texts:
            logger.error(f"No valid content from {source_id}")
            self.results['sources_failed'] += 1
            return
        
        # Combine all texts from this source
        combined_text = "\n\n".join(all_texts)
        combined_fingerprint = self._fingerprint(combined_text)
        
        # Check for changes
        change_summary = self.differ.compare(source_id, combined_text, combined_fingerprint)
        
        if change_summary.changed:
            logger.info(f"🚨 CHANGE DETECTED in {source_id}!")
            logger.info(f"   Added: {len(change_summary.added_lines)} lines")
            logger.info(f"   Removed: {len(change_summary.removed_lines)} lines")
            logger.info(f"   Changed: {change_summary.percent_changed:.1f}%")
            
            self.results['changes_detected'] += 1
            
            # TODO: Match and notify
            # self._match_and_notify(source, change_summary)
        else:
            logger.info(f"✅ No meaningful change in {source_id}")
    
    def _fingerprint(self, text: str) -> str:
        """Generate fingerprint for text."""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _log_summary(self):
        """Log pipeline summary."""
        logger.info("=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Sources checked: {self.results['sources_checked']}")
        logger.info(f"Sources failed: {self.results['sources_failed']}")
        logger.info(f"Changes detected: {self.results['changes_detected']}")
        logger.info(f"Alerts sent: {self.results['alerts_sent']}")
        
        if self.results['errors']:
            logger.info(f"Errors: {len(self.results['errors'])}")
            for error in self.results['errors'][:5]:
                logger.info(f"  - {error}")
        
        # Single-line summary for cron
        summary_line = (
            f"PIPELINE_COMPLETE: checked={self.results['sources_checked']} "
            f"failed={self.results['sources_failed']} "
            f"changes={self.results['changes_detected']} "
            f"alerts={self.results['alerts_sent']}"
        )
        logger.info(summary_line)
        
        # Save results
        results_file = self.state_dir / 'last_run.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)


if __name__ == '__main__':
    pipeline = ProductionPipeline()
    exit_code = pipeline.run()
    sys.exit(exit_code)
