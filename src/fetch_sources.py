#!/usr/bin/env python3
"""
Fetch worker: Downloads HTML and linked PDFs from agenda sources.
Uses only standard library (no external dependencies).
"""

import hashlib
import json
import logging
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
LOGS_DIR = Path(__file__).parent.parent / "logs"
MAX_PDFS_PER_PAGE = 10
REQUEST_TIMEOUT = 30
RETRIES = 3
BACKOFF_FACTOR = 1

# Create SSL context that works with more servers
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "fetch.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class FetchWorker:
    def __init__(self):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=SSL_CONTEXT)
        )
        self.opener.addheaders = [
            ('User-Agent', 'LA-Agenda-Alerts/1.0 (Monitoring Service)')
        ]
    
    def _fetch_with_retry(self, url: str, timeout: int = REQUEST_TIMEOUT, stream: bool = False) -> bytes:
        """Fetch URL with retry logic."""
        last_error = None
        for attempt in range(RETRIES):
            try:
                if attempt > 0:
                    time.sleep(BACKOFF_FACTOR * (2 ** attempt))
                
                response = self.opener.open(url, timeout=timeout)
                return response.read()
                
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in (429, 500, 502, 503, 504):
                    logger.warning(f"Retry {attempt + 1}/{RETRIES} for {url}: HTTP {e.code}")
                    continue
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"Retry {attempt + 1}/{RETRIES} for {url}: {e}")
                continue
        
        raise last_error
    
    def fetch_all(self, sources_path: Path) -> Dict:
        """Fetch all sources and return manifest."""
        timestamp = datetime.now()
        run_dir = DATA_DIR / timestamp.strftime("%Y-%m-%d") / timestamp.strftime("%H%M")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        manifest = {
            "timestamp": timestamp.isoformat(),
            "run_id": timestamp.strftime("%Y%m%d_%H%M%S"),
            "sources": []
        }
        
        with open(sources_path) as f:
            sources_config = json.load(f)
        
        for source in sources_config["sources"]:
            source_result = self._fetch_source(source, run_dir)
            manifest["sources"].append(source_result)
        
        # Write manifest
        manifest_path = run_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Fetch complete. Manifest: {manifest_path}")
        return manifest
    
    def _fetch_source(self, source: Dict, run_dir: Path) -> Dict:
        """Fetch a single source."""
        source_id = source["id"]
        source_dir = run_dir / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            "source_id": source_id,
            "source_name": source["name"],
            "urls": []
        }
        
        for url in source["urls"]:
            url_result = self._fetch_url(url, source_dir)
            result["urls"].append(url_result)
        
        return result
    
    def _fetch_url(self, url: str, source_dir: Path) -> Dict:
        """Fetch a single URL and linked PDFs."""
        result = {
            "url": url,
            "status": "pending",
            "html_file": None,
            "pdfs": [],
            "error": None
        }
        
        try:
            logger.info(f"Fetching: {url}")
            html_content = self._fetch_with_retry(url)
            html_text = html_content.decode('utf-8', errors='replace')
            
            # Save HTML
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            html_file = source_dir / f"page_{url_hash}.html"
            html_file.write_bytes(html_content)
            result["html_file"] = str(html_file.relative_to(DATA_DIR.parent.parent))
            
            # Find and download PDFs
            pdf_urls = self._extract_pdf_urls(html_text, url)
            pdfs_to_download = pdf_urls[:MAX_PDFS_PER_PAGE]
            
            for i, pdf_url in enumerate(pdfs_to_download):
                pdf_result = self._download_pdf(pdf_url, source_dir, i)
                result["pdfs"].append(pdf_result)
            
            result["status"] = "success"
            logger.info(f"Success: {url} ({len(result['pdfs'])} PDFs)")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Failed: {url} - {e}")
        
        return result
    
    def _extract_pdf_urls(self, html: str, base_url: str) -> List[str]:
        """Extract PDF URLs from HTML."""
        pdf_urls = []
        
        # Find href attributes
        href_pattern = r'href=["\'](.*?\.pdf)["\']'
        matches = re.findall(href_pattern, html, re.IGNORECASE)
        
        for href in matches:
            full_url = urljoin(base_url, href)
            pdf_urls.append(full_url)
        
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for url in pdf_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def _download_pdf(self, pdf_url: str, source_dir: Path, index: int) -> Dict:
        """Download a PDF file."""
        result = {
            "url": pdf_url,
            "file": None,
            "sha256": None,
            "size": 0,
            "status": "pending",
            "error": None
        }
        
        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            pdf_content = self._fetch_with_retry(pdf_url)
            
            # Generate filename
            parsed = urlparse(pdf_url)
            basename = Path(parsed.path).name or f"document_{index}.pdf"
            basename = re.sub(r'[^\w\-\.]', '_', basename)
            pdf_file = source_dir / basename
            
            # Save and hash
            sha256 = hashlib.sha256(pdf_content).hexdigest()
            pdf_file.write_bytes(pdf_content)
            
            result["file"] = str(pdf_file.relative_to(DATA_DIR.parent.parent))
            result["sha256"] = sha256
            result["size"] = len(pdf_content)
            result["status"] = "success"
            
            logger.info(f"PDF saved: {basename} ({len(pdf_content)} bytes)")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"PDF failed: {pdf_url} - {e}")
        
        return result


def main():
    """Main entry point."""
    sources_path = Path(__file__).parent / "sources.json"
    
    if not sources_path.exists():
        logger.error(f"Sources file not found: {sources_path}")
        sys.exit(1)
    
    worker = FetchWorker()
    manifest = worker.fetch_all(sources_path)
    
    # Print summary
    success_count = sum(1 for s in manifest["sources"] if all(u["status"] == "success" for u in s["urls"]))
    total_count = len(manifest["sources"])
    
    logger.info(f"Fetch complete: {success_count}/{total_count} sources successful")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
