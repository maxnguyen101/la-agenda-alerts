#!/usr/bin/env python3
"""
Production-Ready Agenda Discovery with Recursive Navigation
"""

import gzip
import hashlib
import io
import logging
import random
import re
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import urllib.request
import urllib.error

# PDF imports
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ParsedDoc:
    """Result of parsing a document."""
    text: str
    page_count: int = 0
    parse_warnings: List[str] = None
    confidence: float = 0.0
    fingerprint: str = ""
    source_url: str = ""
    doc_type: str = "unknown"  # agenda, calendar, minutes, index, unknown
    
    def __post_init__(self):
        if self.parse_warnings is None:
            self.parse_warnings = []
        if not self.fingerprint and self.text:
            normalized = self._normalize_for_fingerprint(self.text)
            self.fingerprint = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def _normalize_for_fingerprint(text: str) -> str:
        lines = text.lower().split('\n')
        lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
        lines = sorted([l for l in lines if len(l) > 3])
        return '\n'.join(lines)


class ProductionFetcher:
    """Production-grade fetcher with rate limiting and resilience."""
    
    def __init__(self, cache_dir: Path, timeout: int = 30, bypass_cache: bool = False):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.bypass_cache = bypass_cache
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self.last_fetch: Dict[str, float] = {}
        self.min_delay = 2.0
        
    def fetch(self, url: str, source_id: str) -> Tuple[Optional[bytes], Dict]:
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
            'gzip_detected': False,
            'cache_bypassed': self.bypass_cache
        }
        
        if self.bypass_cache:
            logger.info(f"Cache bypassed for {source_id}")
        else:
            cached = self._get_cached(url)
            if cached and self._is_cache_fresh(cached, hours=1):
                metadata['cached'] = True
                metadata['sha256'] = cached['sha256']
                return cached['content'], metadata
        
        self._rate_limit(domain)
        
        for attempt in range(3):
            try:
                content, response_meta = self._fetch_once(url)
                metadata.update(response_meta)
                
                if content is not None:
                    metadata['sha256'] = hashlib.sha256(content).hexdigest()
                    if not self.bypass_cache:
                        self._cache_content(url, content, metadata)
                    return content, metadata
                    
            except urllib.error.HTTPError as e:
                metadata['status_code'] = e.code
                if e.code in (404, 410):
                    metadata['error'] = f'HTTP {e.code}'
                    return None, metadata
                elif e.code == 429:
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                elif e.code >= 500:
                    time.sleep(self._exponential_backoff(attempt))
                    continue
                else:
                    metadata['error'] = f'HTTP {e.code}'
                    return None, metadata
            except Exception as e:
                metadata['error'] = str(e)
                time.sleep(self._exponential_backoff(attempt))
        
        return None, metadata
    
    def _fetch_once(self, url: str) -> Tuple[Optional[bytes], Dict]:
        request = urllib.request.Request(url, headers=self.headers)
        response = urllib.request.urlopen(request, timeout=self.timeout, context=self.ssl_context)
        
        meta = {
            'status_code': response.getcode(),
            'content_type': response.headers.get('Content-Type', 'unknown'),
        }
        
        content = response.read()
        
        # Handle gzip
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        if content_encoding == 'gzip' or content[:2] == b'\x1f\x8b':
            meta['gzip_detected'] = True
            try:
                content = gzip.decompress(content)
            except Exception as e:
                logger.warning(f"Gzip decompression failed: {e}")
        
        return content, meta
    
    def _rate_limit(self, domain: str):
        now = time.time()
        if domain in self.last_fetch:
            elapsed = now - self.last_fetch[domain]
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
        self.last_fetch[domain] = now
    
    def _exponential_backoff(self, attempt: int) -> float:
        return min(2 ** attempt, 60) + random.uniform(0, 1)
    
    def _get_cached(self, url: str) -> Optional[Dict]:
        if self.bypass_cache:
            return None
        cache_file = self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"
        if cache_file.exists():
            import json
            with open(cache_file) as f:
                return json.load(f)
        return None
    
    def _cache_content(self, url: str, content: bytes, metadata: Dict):
        if self.bypass_cache:
            return
        cache_file = self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"
        import json
        with open(cache_file, 'w') as f:
            json.dump({'content': content.hex(), 'sha256': metadata['sha256'], 
                      'cached_at': datetime.now().isoformat(), **metadata}, f)
    
    def _is_cache_fresh(self, cached: Dict, hours: int = 1) -> bool:
        cached_time = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
        return (datetime.now() - cached_time).total_seconds() < hours * 3600


class DocumentClassifier:
    """Classifies documents as agenda, calendar, minutes, or index."""
    
    @staticmethod
    def classify(text: str) -> str:
        text_lower = text.lower()[:2000]  # Check first 2000 chars
        
        # Agenda indicators
        agenda_indicators = ['agenda', 'agenda item', 'order of business', 'call to order',
                           'item no', 'item #', 'resolution no', 'motion']
        has_agenda = any(ind in text_lower for ind in agenda_indicators)
        
        # Calendar indicators
        calendar_indicators = ['calendar', 'meeting calendar', 'schedule of meetings']
        has_calendar = any(ind in text_lower for ind in calendar_indicators)
        
        # Minutes indicators
        minutes_indicators = ['minutes', 'meeting minutes', 'approved minutes']
        has_minutes = any(ind in text_lower for ind in minutes_indicators)
        
        # Classification logic
        if has_agenda and not has_calendar:
            return 'agenda'
        elif has_calendar and not has_agenda:
            return 'calendar'
        elif has_minutes and not has_agenda:
            return 'minutes'
        elif len(text) < 5000 and text.count('http') > 10:
            return 'index'  # Likely an index/events page
        else:
            return 'unknown'


class RecursiveAgendaDiscovery:
    """Discovers agenda documents with recursive navigation."""
    
    POSITIVE_KEYWORDS = ['agenda', 'packet', 'meeting', 'board', 'commission', 
                        'committee', 'minutes', 'notice', 'hearing', 'council']
    NEGATIVE_KEYWORDS = ['archive', 'subscribe', 'donate', 'contact', 
                        'login', 'search', 'newsletter', 'rss', 'feed']
    DATE_PATTERNS = [r'\d{4}', r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*',
                     r'\d{1,2}/\d{1,2}', r'\d{1,2}-\d{1,2}']
    
    def __init__(self, fetcher: ProductionFetcher):
        self.fetcher = fetcher
        self.classifier = DocumentClassifier()
    
    def score_link(self, href: str, anchor_text: str, base_url: str) -> int:
        score = 0
        href_lower = href.lower()
        text_lower = anchor_text.lower()
        combined = href_lower + ' ' + text_lower
        href_filename = href_lower.split('/')[-1].split('?')[0]
        
        if href_lower.endswith('.pdf'):
            score += 25
        
        if 'calendar' in href_filename:
            score -= 30
        if 'calendar' in text_lower and 'agenda' not in text_lower:
            score -= 15
        
        if 'agenda packet' in combined:
            score += 20
        elif 'agenda' in combined:
            if any(kw in combined for kw in ['packet', 'materials', 'meeting']):
                score += 15
            else:
                score += 10
        
        for keyword in self.POSITIVE_KEYWORDS:
            if keyword in combined and keyword != 'agenda':
                score += 10
                break
        
        for pattern in self.DATE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                score += 12
                break
        
        base_domain = urlparse(base_url).netloc
        link_domain = urlparse(urljoin(base_url, href)).netloc
        if base_domain == link_domain or not link_domain:
            score += 8
        
        for keyword in self.NEGATIVE_KEYWORDS:
            if keyword in combined:
                score -= 10
                break
        
        return score
    
    def extract_links(self, html: str, base_url: str) -> List[Dict]:
        links = []
        pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for href, anchor_html in matches:
            anchor_text = re.sub(r'<[^>]+>', ' ', anchor_html).strip()
            anchor_text = re.sub(r'\s+', ' ', anchor_text)
            absolute_url = urljoin(base_url, href)
            score = self.score_link(href, anchor_text, base_url)
            
            links.append({'url': absolute_url, 'href': href, 
                         'anchor_text': anchor_text[:100], 'score': score})
        
        links.sort(key=lambda x: x['score'], reverse=True)
        return links
    
    def discover_agenda(self, landing_url: str, source_id: str, max_depth: int = 2) -> Dict:
        """
        Recursively discover agenda document.
        Returns dict with full discovery path and final result.
        """
        result = {
            'landing_url': landing_url,
            'depth_used': 0,
            'discovery_path': [],
            'final_url': None,
            'final_content': None,
            'final_metadata': None,
            'final_parsed': None,
            'error': None
        }
        
        current_url = landing_url
        
        for depth in range(max_depth + 1):
            result['depth_used'] = depth
            
            # Fetch current page
            content, metadata = self.fetcher.fetch(current_url, f"{source_id}_d{depth}")
            
            if not content or metadata.get('status_code') != 200:
                result['error'] = f"Failed to fetch at depth {depth}: {metadata.get('error')}"
                return result
            
            # Try to parse as document
            is_pdf = current_url.lower().endswith('.pdf') or 'pdf' in metadata.get('content_type', '')
            
            if is_pdf:
                # Parse PDF
                parsed = self._parse_pdf(content, current_url)
                doc_type = self.classifier.classify(parsed.text)
                
                step = {
                    'depth': depth,
                    'url': current_url,
                    'type': 'PDF',
                    'doc_type': doc_type,
                    'score': 100  # PDFs are good
                }
                result['discovery_path'].append(step)
                
                if doc_type == 'agenda':
                    result['final_url'] = current_url
                    result['final_content'] = content
                    result['final_metadata'] = metadata
                    result['final_parsed'] = parsed
                    return result
                else:
                    # Wrong type, need to go back and find another link
                    result['error'] = f"PDF is {doc_type}, not agenda"
                    return result
            else:
                # HTML page - extract links and continue
                html = content.decode('utf-8', errors='ignore')
                links = self.extract_links(html, current_url)
                
                if not links:
                    result['error'] = f"No links found at depth {depth}"
                    return result
                
                # Score the page itself
                page_score = 0
                if 'agenda' in html.lower():
                    page_score += 20
                if any(x in html.lower() for x in ['packet', 'materials']):
                    page_score += 15
                
                step = {
                    'depth': depth,
                    'url': current_url,
                    'type': 'HTML',
                    'links_found': len(links),
                    'top_links': links[:5],
                    'page_score': page_score
                }
                result['discovery_path'].append(step)
                
                # Check if this HTML page IS the agenda (rare but possible)
                if page_score >= 25:
                    parsed = self._parse_html(content, current_url)
                    doc_type = self.classifier.classify(parsed.text)
                    if doc_type == 'agenda':
                        result['final_url'] = current_url
                        result['final_content'] = content
                        result['final_metadata'] = metadata
                        result['final_parsed'] = parsed
                        return result
                
                # Select best link for next depth
                if depth < max_depth:
                    best_link = None
                    for link in links:
                        if link['score'] > 0:
                            best_link = link
                            break
                    
                    if best_link:
                        current_url = best_link['url']
                    else:
                        result['error'] = f"No positive-scoring links at depth {depth}"
                        return result
                else:
                    # At max depth, return best available
                    if links:
                        result['final_url'] = links[0]['url']
                        # Fetch final content
                        final_content, final_meta = self.fetcher.fetch(links[0]['url'], f"{source_id}_final")
                        result['final_content'] = final_content
                        result['final_metadata'] = final_meta
                        if final_content:
                            if links[0]['url'].lower().endswith('.pdf'):
                                result['final_parsed'] = self._parse_pdf(final_content, links[0]['url'])
                            else:
                                result['final_parsed'] = self._parse_html(final_content, links[0]['url'])
                    return result
        
        return result
    
    def _parse_pdf(self, content: bytes, url: str) -> ParsedDoc:
        warnings = []
        text = ""
        page_count = 0
        
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    page_count = len(pdf.pages)
                    pages_text = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            pages_text.append(page_text)
                    text = '\n\n'.join(pages_text)
            except Exception as e:
                warnings.append(f"pdfplumber_error: {e}")
        
        if not text and PYPDF2_AVAILABLE:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                page_count = len(reader.pages)
                pages_text = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                text = '\n\n'.join(pages_text)
            except Exception as e:
                warnings.append(f"pypdf2_error: {e}")
        
        text = self._normalize_text(text)
        doc_type = self.classifier.classify(text)
        
        return ParsedDoc(
            text=text,
            page_count=page_count,
            parse_warnings=warnings,
            confidence=0.7 if len(text) > 1000 else 0.3,
            source_url=url,
            doc_type=doc_type
        )
    
    def _parse_html(self, content: bytes, url: str) -> ParsedDoc:
        try:
            text = content.decode('utf-8', errors='replace')
        except:
            text = content.decode('latin-1', errors='replace')
        
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        
        main_content = self._extract_main_content(text)
        if main_content:
            text = main_content
        else:
            text = re.sub(r'<[^>]+>', ' ', text)
        
        text = self._normalize_text(text)
        doc_type = self.classifier.classify(text)
        
        return ParsedDoc(
            text=text,
            page_count=1,
            confidence=0.5 if len(text) > 500 else 0.2,
            source_url=url,
            doc_type=doc_type
        )
    
    def _extract_main_content(self, html: str) -> Optional[str]:
        patterns = [
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*main[^"\']*["\'][^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                largest = max(matches, key=len)
                if len(largest) > 500:
                    return re.sub(r'<[^>]+>', ' ', largest)
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        
        # Remove page numbers
        text = re.sub(r'\b[Pp]age\s+\d+\s+(of|/)\s+\d+\b', '', text)
        text = re.sub(r'\b[Pp]age\s+\d+\b', '', text)
        
        # Remove timestamps
        text = re.sub(r'\b[Pp]rinted\s+(on|at)\s+[^\n]+', '', text)
        text = re.sub(r'\b[Uu]pdated\s+(on|at)?\s*[^\n]+', '', text)
        text = re.sub(r'\b[Gg]enerated\s+(on|at)?\s*[^\n]+', '', text)
        
        # Collapse whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()
    
    def extract_meeting_facts(self, parsed: ParsedDoc) -> Dict:
        text = parsed.text
        lines = text.split('\n')
        
        facts = {
            'meeting_date': 'NOT FOUND',
            'meeting_time': 'NOT FOUND',
            'committee': 'NOT FOUND',
            'location': 'NOT FOUND',
            'agenda_items': []
        }
        
        date_patterns = [
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', 'month_day_year'),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', 'abbrev_month'),
            (r'\d{1,2}/\d{1,2}/\d{4}', 'slash_date'),
            (r'\d{1,2}-\d{1,2}-\d{4}', 'dash_date'),
        ]
        
        time_pattern = r'\d{1,2}:\d{2}\s*(AM|PM|am|pm|a\.m\.|p\.m\.)'
        
        committee_patterns = [
            r'(board\s+of\s+\w+)',
            r'(city\s+council)',
            r'(planning\s+commission)',
            r'(committee\s+on\s+\w+)',
            r'(metro\s+board)',
        ]
        
        location_keywords = ['location:', 'address:', 'zoom:', 'meeting location', 'board room', 'city hall', 'chambers']
        
        for line in lines[:300]:
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) < 3:
                continue
            
            line_lower = line_stripped.lower()
            
            for pattern, _ in date_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match and facts['meeting_date'] == 'NOT FOUND':
                    facts['meeting_date'] = match.group(0)
                    break
            
            time_match = re.search(time_pattern, line_stripped, re.IGNORECASE)
            if time_match and facts['meeting_time'] == 'NOT FOUND':
                facts['meeting_time'] = time_match.group(0)
            
            for pattern in committee_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match and facts['committee'] == 'NOT FOUND':
                    facts['committee'] = match.group(0).title()
                    break
            
            for keyword in location_keywords:
                if keyword in line_lower and facts['location'] == 'NOT FOUND':
                    if ':' in line_stripped:
                        parts = line_stripped.split(':', 1)
                        if len(parts) > 1 and len(parts[1].strip()) > 5:
                            facts['location'] = parts[1].strip()[:120]
                        else:
                            facts['location'] = line_stripped[:120]
                    else:
                        facts['location'] = line_stripped[:120]
                    break
            
            if re.match(r'^\d+[\.\)]\s+', line_stripped) or re.match(r'^[•\-\*]\s+', line_stripped):
                if len(line_stripped) > 20 and len(facts['agenda_items']) < 10:
                    item = re.sub(r'^[\d•\-\*\.\)]+\s*', '', line_stripped)
                    if len(item) > 15:
                        facts['agenda_items'].append(item[:150])
        
        return facts
