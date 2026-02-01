#!/usr/bin/env python3
"""
Production Fetcher - Hardened with retries, caching, and resilience
"""

import hashlib
import json
import logging
import random
import re
import ssl
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class ProductionFetcher:
    """Hardened fetcher with caching, retries, and error handling."""
    
    def __init__(self, cache_dir: Path, timeout: int = 30):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        
        # Standard headers to look like a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # SSL context that works with more servers
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Per-source rate limiting (domain -> last_fetch_time)
        self.last_fetch: Dict[str, float] = {}
        self.min_delay = 2.0  # Minimum seconds between requests to same domain
        
    def fetch(self, url: str, source_id: str) -> Tuple[Optional[bytes], Dict]:
        """
        Fetch URL with full hardening.
        
        Returns: (content_bytes, metadata_dict)
        metadata includes: status_code, content_type, sha256, cached, error
        """
        domain = urlparse(url).netloc
        metadata = {
            'url': url,
            'source_id': source_id,
            'fetched_at': datetime.now().isoformat(),
            'status_code': None,
            'content_type': None,
            'sha256': None,
            'cached': False,
            'error': None,
            'retries': 0
        }
        
        # Rate limiting
        self._rate_limit(domain)
        
        # Try to use cached version if recent (with conditional request)
        cached = self._get_cached(url)
        if cached and self._is_cache_fresh(cached, hours=1):
            logger.info(f"Using fresh cache for {source_id}")
            metadata['cached'] = True
            metadata['sha256'] = cached['sha256']
            return cached['content'], metadata
        
        # Attempt fetch with retries
        content = None
        for attempt in range(3):
            metadata['retries'] = attempt
            try:
                content, response_meta = self._fetch_once(url, cached)
                metadata.update(response_meta)
                
                if content is not None:
                    # Success - cache it
                    metadata['sha256'] = hashlib.sha256(content).hexdigest()
                    self._cache_content(url, content, metadata)
                    logger.info(f"✅ Fetched {source_id}: {len(content)} bytes")
                    return content, metadata
                    
            except urllib.error.HTTPError as e:
                metadata['status_code'] = e.code
                if e.code in (404, 410):
                    logger.error(f"❌ {source_id}: Page not found ({e.code})")
                    metadata['error'] = f'HTTP {e.code} - Page removed or changed'
                    return None, metadata
                elif e.code == 403:
                    logger.error(f"❌ {source_id}: Access forbidden (403)")
                    metadata['error'] = 'HTTP 403 - Access blocked'
                    return None, metadata
                elif e.code == 429:
                    logger.warning(f"⚠️ {source_id}: Rate limited (429), backing off...")
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                elif e.code >= 500:
                    logger.warning(f"⚠️ {source_id}: Server error ({e.code}), retrying...")
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                else:
                    metadata['error'] = f'HTTP {e.code}'
                    return None, metadata
                    
            except Exception as e:
                logger.error(f"❌ {source_id}: Fetch error: {e}")
                metadata['error'] = str(e)
                time.sleep(self._exponential_backoff(attempt))
        
        # All retries failed
        logger.error(f"❌ {source_id}: Failed after 3 attempts")
        if metadata['error'] is None:
            metadata['error'] = 'Max retries exceeded'
        return None, metadata
    
    def _fetch_once(self, url: str, cached: Optional[Dict]) -> Tuple[Optional[bytes], Dict]:
        """Single fetch attempt with conditional request support."""
        req_headers = self.headers.copy()
        
        # Add conditional headers if we have cached version
        if cached:
            if 'etag' in cached:
                req_headers['If-None-Match'] = cached['etag']
            if 'last_modified' in cached:
                req_headers['If-Modified-Since'] = cached['last_modified']
        
        request = urllib.request.Request(url, headers=req_headers)
        
        response = urllib.request.urlopen(
            request, 
            timeout=self.timeout,
            context=self.ssl_context
        )
        
        meta = {
            'status_code': response.getcode(),
            'content_type': response.headers.get('Content-Type', 'unknown'),
            'etag': response.headers.get('ETag'),
            'last_modified': response.headers.get('Last-Modified')
        }
        
        # Handle 304 Not Modified
        if response.getcode() == 304 and cached:
            logger.info(f"304 Not Modified for {url}")
            return cached['content'], meta
        
        content = response.read()
        return content, meta
    
    def _rate_limit(self, domain: str):
        """Enforce rate limiting per domain."""
        now = time.time()
        if domain in self.last_fetch:
            elapsed = now - self.last_fetch[domain]
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self.last_fetch[domain] = now
    
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate backoff with jitter."""
        base = min(2 ** attempt, 60)  # Max 60 seconds
        jitter = random.uniform(0, 1)
        return base + jitter
    
    def _get_cached(self, url: str) -> Optional[Dict]:
        """Get cached content for URL."""
        cache_key = self._cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            # Load binary content
            content_file = self.cache_dir / f"{cache_key}.bin"
            if content_file.exists():
                with open(content_file, 'rb') as f:
                    cached['content'] = f.read()
                return cached
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        return None
    
    def _cache_content(self, url: str, content: bytes, metadata: Dict):
        """Cache content and metadata."""
        cache_key = self._cache_key(url)
        
        # Save metadata
        meta_to_save = metadata.copy()
        meta_to_save.pop('content', None)  # Don't duplicate
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(meta_to_save, f, indent=2)
        
        # Save binary content
        content_file = self.cache_dir / f"{cache_key}.bin"
        with open(content_file, 'wb') as f:
            f.write(content)
    
    def _cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def _is_cache_fresh(self, cached: Dict, hours: int = 1) -> bool:
        """Check if cached content is fresh enough."""
        if 'fetched_at' not in cached:
            return False
        try:
            fetched = datetime.fromisoformat(cached['fetched_at'])
            age = datetime.now() - fetched
            return age.total_seconds() < (hours * 3600)
        except:
            return False
    
    def clean_old_cache(self, max_age_days: int = 7):
        """Remove cache files older than max_age_days."""
        cutoff = time.time() - (max_age_days * 86400)
        removed = 0
        
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                if cache_file.stat().st_mtime < cutoff:
                    cache_file.unlink()
                    # Also remove binary if exists
                    bin_file = cache_file.with_suffix('.bin')
                    if bin_file.exists():
                        bin_file.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(f"Cache cleanup error: {e}")
        
        if removed > 0:
            logger.info(f"Cleaned {removed} old cache files")


if __name__ == '__main__':
    # Test
    import logging
    logging.basicConfig(level=logging.INFO)
    
    fetcher = ProductionFetcher(Path('/tmp/test_cache'))
    content, meta = fetcher.fetch('https://example.com', 'test')
    print(f"Status: {meta['status_code']}")
    print(f"Cached: {meta['cached']}")
    print(f"Size: {len(content) if content else 0} bytes")
