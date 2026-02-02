#!/usr/bin/env python3
"""
Production-Ready Agenda Discovery with Deep Navigation
KEY FIX: Keeps drilling until finding agenda-like document
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
from typing import Dict, List, Optional, Tuple, Set
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
    doc_type: str = "unknown"  # agenda, calendar, minutes, index, no-agenda-yet, unknown
    
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
    """Production-grade fetcher."""
    
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
        
        if not self.bypass_cache:
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
                data = json.load(f)
                if 'content' in data:
                    data['content'] = bytes.fromhex(data['content'])
                return data
        return None
    
    def _cache_content(self, url: str, content: bytes, metadata: Dict):
        if self.bypass_cache:
            return
        cache_file = self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"
        import json
        data = {**metadata, 'content': content.hex(), 'cached_at': datetime.now().isoformat()}
        with open(cache_file, 'w') as f:
            json.dump(data, f, default=str)
    
    def _is_cache_fresh(self, cached: Dict, hours: int = 1) -> bool:
        cached_time = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
        return (datetime.now() - cached_time).total_seconds() < hours * 3600


class DocumentClassifier:
    """Classifies documents based on content, not just keywords."""
    
    # Navigation terms to strip before classification
    NAV_TERMS = ['home', 'about', 'contact', 'meetings', 'agendas', 'minutes', 
                 'calendar', 'search', 'menu', 'navigation', 'skip to content',
                 'privacy policy', 'terms of use', 'sitemap', 'login', 'logout']
    
    # High-signal agenda phrases
    AGENDA_PHRASES = ['call to order', 'roll call', 'public comment', 'adjournment',
                     'closed session', 'agenda item', 'item no.', 'item #', 
                     'action item', 'consent calendar', 'public hearing']
    
    @staticmethod
    def strip_nav_text(text: str) -> str:
        """Remove navigation-like text before classification."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip very short lines
            if len(line_stripped) < 4:
                continue
            
            # Skip lines that are just navigation terms
            line_lower = line_stripped.lower()
            if line_stripped.lower() in DocumentClassifier.NAV_TERMS:
                continue
            
            # Skip lines containing navigation terms as standalone words
            is_nav = False
            for term in DocumentClassifier.NAV_TERMS:
                if re.search(r'\b' + re.escape(term) + r'\b', line_lower):
                    # Check if it's just the nav term with minimal other content
                    if len(line_stripped) < len(term) + 10:
                        is_nav = True
                        break
            
            if not is_nav:
                cleaned_lines.append(line_stripped)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def count_item_markers(text: str) -> int:
        """Count distinct item markers at line starts."""
        lines = text.split('\n')
        markers = set()
        
        for line in lines:
            line_stripped = line.strip()
            # Numbered patterns: 1., 1), 1]
            if re.match(r'^\d+[\.\)\]]', line_stripped):
                markers.add(re.match(r'^(\d+)', line_stripped).group(1))
            # Lettered patterns: A., A), a.
            elif re.match(r'^[A-Za-z][\.\)\]]', line_stripped):
                markers.add(re.match(r'^([A-Za-z])', line_stripped).group(1).upper())
            # Roman numerals: I., II., i.
            elif re.match(r'^[IVXivx]+[\.\)\]]', line_stripped):
                markers.add('ROMAN')
        
        return len(markers)
    
    @staticmethod
    def classify(text: str) -> str:
        """Classify document based on cleaned content."""
        # Strip navigation text first
        cleaned_text = DocumentClassifier.strip_nav_text(text)
        cleaned_lower = cleaned_text.lower()[:5000]  # Check first 5000 chars of cleaned text
        
        # Check for high-signal agenda phrases
        has_agenda_phrase = any(phrase in cleaned_lower for phrase in DocumentClassifier.AGENDA_PHRASES)
        
        # Count item markers
        item_marker_count = DocumentClassifier.count_item_markers(cleaned_text)
        
        # Check for generic "agenda" keyword (without high-signal phrases)
        has_generic_agenda = 'agenda' in cleaned_lower and not has_agenda_phrase
        
        # Calendar indicators (in cleaned text)
        calendar_indicators = ['meeting calendar', 'schedule of meetings', 'calendar year',
                              'fy20', 'fiscal year']
        has_calendar = any(ind in cleaned_lower for ind in calendar_indicators)
        
        # Minutes indicators
        minutes_indicators = ['meeting minutes', 'approved minutes', 'minutes of',
                             'the meeting was called to order', 'present:']
        has_minutes = any(ind in cleaned_lower for ind in minutes_indicators)
        
        # No agenda yet indicators
        no_agenda_indicators = ['no agenda', 'agenda not yet', 'agenda will be posted', 
                               'not available', 'coming soon', 'check back later',
                               'agenda has not been posted']
        has_no_agenda = any(ind in cleaned_lower for ind in no_agenda_indicators)
        
        # Index page indicators
        index_indicators = ['upcoming meetings', 'meeting list', 'all meetings', 
                          'select a meeting', 'filter by', 'search meetings',
                          'browse by', 'category:', 'tags:']
        has_index = any(ind in cleaned_lower for ind in index_indicators)
        
        # Classification logic
        if has_no_agenda and not has_agenda_phrase:
            return 'no-agenda-yet'
        elif has_agenda_phrase:
            return 'agenda'
        elif item_marker_count >= 5:
            return 'agenda'
        elif has_calendar and not has_agenda_phrase and item_marker_count < 3:
            return 'calendar'
        elif has_minutes and not has_agenda_phrase:
            return 'minutes'
        elif has_index or has_generic_agenda or (len(cleaned_text) < 2000 and text.count('http') > 5):
            return 'index'
        else:
            return 'unknown'


class DeepAgendaDiscovery:
    """
    Deep agenda discovery that keeps drilling until finding agenda-like documents.
    KEY FIX: Uses visited set, max depth 3, and classifier-based rejection.
    """
    
    # Source-specific patterns
    SOURCE_PATTERNS = {
        'metro_board': {
            'mode': 'meeting_list',  # Special mode for Metro
            'landing': 'https://boardagendas.metro.net/',
            'fallback': 'https://metro.legistar.com/MainBody.aspx',
            'allowlist': ['/event/', 'agenda', 'packet', '.pdf', '/events/'],
            'blocklist': ['/calendar', 'fy26-committee-board-calendar', 'calendar.pdf', 
                         '/board-members', '/committees', '/minutes/'],
            'scoring': {
                'agenda_pdf': 40,      # +40 if href contains "agenda" and endswith ".pdf"
                'agenda_packet': 30,   # +30 if anchor text contains "agenda packet"
                'packet_materials': 20, # +20 if href contains "packet" or "meeting materials"
                'calendar': -40         # -40 if href filename contains "calendar"
            }
        },
        'county_bos': {
            'mode': 'standard',
            'landing': 'https://bos.lacounty.gov/',
            'allowlist': ['/agenda', '/agendas', '/board-meeting', '/meeting-materials',
                         'board agenda', 'meeting agenda', '.pdf'],
            'blocklist': ['/rules', '/district', '/map', '/about', '/contact',
                         'rules-of-the-board', 'district-map'],
            'depth_preference': 'deep'
        },
        'city_council': {
            'mode': 'api_first',  # Try API first, then crawl
            'landing': 'https://clerk.lacity.gov/',
            'api_patterns': ['api', 'json', 'events', 'meeting', 'agenda', 'attachments'],
            'allowlist': ['/agenda', '/agendas', '/council-agenda', '/meeting-agenda',
                         '/council-file', '/cf-', 'agenda.pdf', 'council-agenda'],
            'blocklist': ['/search', '/category', '/tag', '/author', '/page/',
                         '/subscribe'],
            'depth_preference': 'deep'
        },
        'lahd_commissions': {
            'mode': 'html_agenda_list',  # This is already a structured agenda list
            'landing': 'https://ens.lacity.org/lahd/ens_lahd_commagd.htm',
            'allowlist': ['.pdf', 'agenda', 'commission', 'meeting', 
                         '/wp-content/uploads/', 'rac', 'csac', 'hhs'],  # Commission abbreviations
            'blocklist': ['/news', '/about', '/contact', 'calendar'],
            'depth_preference': 'shallow'  # Don't need deep recursion
        },
        'lahd_rac': {
            'mode': 'pdf_focused',  # RAC agendas are PDF-focused
            'landing': 'https://housing.lacity.gov/category/community-resources/commissions-advisory-boards',
            'allowlist': ['rac', 'agenda', '.pdf', '/wp-content/uploads/',
                         'rent adjustment', 'commission'],
            'blocklist': ['/news', '/about', '/contact', 'calendar', 'minutes'],
            'scoring': {
                'rac_agenda_pdf': 50,   # High priority for RAC agenda PDFs
                'agenda_pdf': 40,
                'rac_keyword': 25       # Boost for "RAC" mentions
            }
        }
    }
    
    def __init__(self, fetcher: ProductionFetcher):
        self.fetcher = fetcher
        self.classifier = DocumentClassifier()
    
    def score_link_v2(self, href: str, anchor_text: str, base_url: str, 
                     source_id: str, depth: int) -> int:
        """
        NEW SCORING with PDF-first + agenda-first rules.
        """
        score = 0
        href_lower = href.lower()
        text_lower = anchor_text.lower()
        combined = href_lower + ' ' + text_lower
        href_filename = href_lower.split('/')[-1].split('?')[0]
        
        is_pdf = href_lower.endswith('.pdf')
        
        # Get source patterns
        patterns = self.SOURCE_PATTERNS.get(source_id, {})
        allowlist = patterns.get('allowlist', [])
        blocklist = patterns.get('blocklist', [])
        
        # Source-specific allowlist boost
        for pattern in allowlist:
            if pattern in href_lower or pattern in text_lower:
                score += 30
                break
        
        # Source-specific blocklist penalty
        for pattern in blocklist:
            if pattern in href_lower:
                score -= 50
                break
        
        # +40 if href contains "agenda" AND ends with .pdf
        if 'agenda' in href_lower and is_pdf:
            score += 40
        
        # +25 if href contains "agenda" (any type)
        elif 'agenda' in combined:
            score += 25
        
        # +20 if anchor text contains "agenda packet"
        if 'agenda packet' in text_lower:
            score += 20
        
        # +15 if packet/materials
        if any(kw in combined for kw in ['packet', 'materials', 'meeting materials']):
            score += 15
        
        # +25 for PDF (base score)
        if is_pdf:
            score += 25
        
        # +10 for meeting keywords
        if any(kw in combined for kw in ['meeting', 'board', 'committee', 'council']):
            score += 10
        
        # +12 for date patterns
        date_patterns = [r'\d{4}', r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', 
                        r'\d{1,2}/\d{1,2}']
        for pattern in date_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                score += 12
                break
        
        # +8 for same domain
        base_domain = urlparse(base_url).netloc
        link_domain = urlparse(urljoin(base_url, href)).netloc
        if base_domain == link_domain or not link_domain:
            score += 8
        
        # -40 if href filename contains "calendar"
        if 'calendar' in href_filename:
            score -= 40
        
        # Penalty for generic navigation
        if any(kw in href_lower for kw in ['/search', '/contact', '/about', '/login']):
            score -= 20
        
        return score
    
    def extract_links_v2(self, html: str, base_url: str, source_id: str, depth: int) -> List[Dict]:
        """Extract and score links."""
        links = []
        pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for href, anchor_html in matches:
            anchor_text = re.sub(r'<[^>]+>', ' ', anchor_html).strip()
            anchor_text = re.sub(r'\s+', ' ', anchor_text)
            
            # Skip non-http links
            if href.startswith('#') or href.startswith('javascript:'):
                continue
                
            absolute_url = urljoin(base_url, href)
            score = self.score_link_v2(href, anchor_text, base_url, source_id, depth)
            
            links.append({
                'url': absolute_url,
                'href': href,
                'anchor_text': anchor_text[:100],
                'score': score
            })
        
        links.sort(key=lambda x: x['score'], reverse=True)
        return links
    
    def scan_for_api_endpoints(self, html: str) -> List[str]:
        """Scan HTML for potential API endpoints."""
        endpoints = []
        
        # Look for API patterns in script tags, data attributes, etc.
        patterns = [
            r'["\']([^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*json[^"\']*)["\']',
            r'data-endpoint=["\']([^"\']+)["\']',
            r'url:\s*["\']([^"\']+)["\']',
            r'fetch\(["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            endpoints.extend(matches[:5])
        
        return list(set(endpoints))
    
    def discover_agenda_deep(self, landing_url: str, source_id: str, max_depth: int = 3) -> Dict:
        """
        Deep discovery that keeps drilling until finding agenda-like document.
        Uses visited set to avoid loops.
        """
        result = {
            'landing_url': landing_url,
            'depth_reached': 0,
            'discovery_path': [],
            'final_url': None,
            'final_content': None,
            'final_metadata': None,
            'final_parsed': None,
            'all_candidates': [],
            'error': None,
            'status': 'searching'
        }
        
        visited: Set[str] = set()
        current_url = landing_url
        
        # Get source config
        source_config = self.SOURCE_PATTERNS.get(source_id, {})
        source_mode = source_config.get('mode', 'standard')
        
        for depth in range(max_depth + 1):
            result['depth_reached'] = depth
            
            if current_url in visited:
                result['error'] = f"Loop detected at {current_url}"
                result['status'] = 'fail-loop'
                break
            
            visited.add(current_url)
            
            # Fetch current page
            content, metadata = self.fetcher.fetch(current_url, f"{source_id}_d{depth}")
            
            if not content or metadata.get('status_code') != 200:
                result['error'] = f"Failed to fetch at depth {depth}: {metadata.get('error')}"
                result['status'] = 'fail-fetch'
                break
            
            # Determine content type
            is_pdf = current_url.lower().endswith('.pdf') or 'pdf' in metadata.get('content_type', '')
            
            if is_pdf:
                # Parse and classify PDF
                parsed = self._parse_pdf(content, current_url)
                doc_type = parsed.doc_type
                
                step = {
                    'depth': depth,
                    'url': current_url,
                    'type': 'PDF',
                    'doc_type': doc_type,
                    'score': 100,
                    'chars': len(parsed.text)
                }
                result['discovery_path'].append(step)
                result['all_candidates'].append(step)
                
                # Check if this is what we want
                if doc_type == 'agenda':
                    result['final_url'] = current_url
                    result['final_content'] = content
                    result['final_metadata'] = metadata
                    result['final_parsed'] = parsed
                    result['status'] = 'success-agenda'
                    return result
                elif doc_type == 'no-agenda-yet':
                    result['status'] = 'fail-no-agenda-yet'
                    result['error'] = 'Meeting page states no agenda posted yet'
                    return result
                else:
                    # Wrong type, continue searching
                    result['discovery_path'][-1]['rejected'] = f"Type: {doc_type}"
            else:
                # HTML page - extract links
                html = content.decode('utf-8', errors='ignore')
                
                # API-FIRST MODE: Check for API endpoints
                if source_mode == 'api_first' and depth == 0:
                    api_endpoints = self.scan_for_api_endpoints(html)
                    if api_endpoints:
                        step = {
                            'depth': depth,
                            'url': current_url,
                            'type': 'HTML',
                            'api_endpoints_found': api_endpoints
                        }
                        result['discovery_path'].append(step)
                        # Note: For now we continue with normal crawl even if API found
                        # Full API implementation would call endpoints here
                
                links = self.extract_links_v2(html, current_url, source_id, depth)
                
                # MEETING LIST MODE: Extract up to 15 meeting links at depth 0
                if source_mode == 'meeting_list' and depth == 0:
                    meeting_links = [l for l in links if l['score'] > 20][:15]
                    step = {
                        'depth': depth,
                        'url': current_url,
                        'type': 'HTML',
                        'mode': 'meeting_list',
                        'meeting_links_found': len(meeting_links),
                        'top_meeting_links': meeting_links[:5]
                    }
                    result['discovery_path'].append(step)
                
                # Classify the page itself
                parsed_html = self._parse_html(content, current_url)
                page_type = parsed_html.doc_type
                
                # Add step if not already added by special modes
                step = {
                    'depth': depth,
                    'url': current_url,
                    'type': 'HTML',
                    'doc_type': page_type,
                    'links_found': len(links),
                    'top_links': links[:5]
                }
                # Check if we already have a step for this depth
                if not result['discovery_path'] or result['discovery_path'][-1]['depth'] != depth:
                    result['discovery_path'].append(step)
                
                # If this page IS the agenda (rare), use it
                if page_type == 'agenda' and len(parsed_html.text) > 1000:
                    result['final_url'] = current_url
                    result['final_content'] = content
                    result['final_metadata'] = metadata
                    result['final_parsed'] = parsed_html
                    result['status'] = 'success-agenda-html'
                    return result
                
                # Collect candidates for reporting
                for link in links[:15]:
                    result['all_candidates'].append({
                        'depth': depth,
                        'url': link['url'],
                        'score': link['score'],
                        'anchor': link['anchor_text'][:50]
                    })
                
                # Select next link to follow
                if depth < max_depth and links:
                    # Find first non-visited link
                    next_link = None
                    for link in links:
                        if link['url'] not in visited and link['score'] > -20:
                            next_link = link
                            break
                    
                    if next_link:
                        current_url = next_link['url']
                        result['discovery_path'][-1]['selected_next'] = next_link['url']
                    else:
                        result['error'] = f"No unvisited positive-scoring links at depth {depth}"
                        result['status'] = 'fail-no-links'
                        break
                else:
                    # At max depth
                    result['error'] = f"Reached max depth ({max_depth}) without finding agenda"
                    result['status'] = 'fail-max-depth'
                    break
        
        return result
    
    def _parse_pdf(self, content: bytes, url: str) -> ParsedDoc:
        """Parse PDF document."""
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
        """Parse HTML document."""
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
        """Extract main content area from HTML."""
        patterns = [
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*id=["\']content["\'][^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                largest = max(matches, key=len)
                if len(largest) > 500:
                    return re.sub(r'<[^>]+>', ' ', largest)
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for diffing."""
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
    
    def extract_agenda_items_4tier(self, text: str) -> List[str]:
        """4-tier agenda item extraction."""
        lines = text.split('\n')
        items = []
        used_lines = set()  # Track used lines to avoid duplicates
        
        # Tier 1: Numbered list patterns (1., 1), 1], etc.)
        for line in lines:
            line_stripped = line.strip()
            if line_stripped in used_lines:
                continue
            if re.match(r'^\d+[\.\)\]]\s+', line_stripped):
                if len(line_stripped) > 20:
                    item = re.sub(r'^[\d\.\)\]]+\s*', '', line_stripped)
                    if len(item) > 15:
                        items.append(item[:150])
                        used_lines.add(line_stripped)
                        if len(items) >= 10:
                            break
        
        # Tier 2: Lettered patterns (A., B), a., etc.)
        if len(items) < 3:
            for line in lines:
                line_stripped = line.strip()
                if line_stripped in used_lines:
                    continue
                if re.match(r'^[A-Za-z][\.\)\]]\s+', line_stripped):
                    if len(line_stripped) > 20:
                        item = re.sub(r'^[A-Za-z\.\)\]]+\s*', '', line_stripped)
                        if len(item) > 15:
                            items.append(item[:150])
                            used_lines.add(line_stripped)
                            if len(items) >= 10:
                                break
        
        # Tier 3: "Item" patterns ("Item 1", "Item No.", "Item #")
        if len(items) < 3:
            for line in lines:
                line_stripped = line.strip()
                if line_stripped in used_lines:
                    continue
                if re.search(r'\b[Ii]tem\s*[\d#\.]', line_stripped):
                    if len(line_stripped) > 25:
                        # Clean up "Item X" prefix
                        item = re.sub(r'^[\s\-]*[Ii]tem\s*[\d#\.]+[:\-\s]*', '', line_stripped)
                        if len(item) > 15:
                            items.append(item[:150])
                            used_lines.add(line_stripped)
                            if len(items) >= 10:
                                break
        
        # Tier 4: Heading fallback - top 5 longest distinct non-boilerplate lines
        if len(items) < 3:
            # Filter out boilerplate
            boilerplate = ['agenda', 'minutes', 'meeting', 'call to order', 
                          'adjournment', 'roll call', 'public comment']
            candidates = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped in used_lines:
                    continue
                if len(line_stripped) > 30 and len(line_stripped) < 200:
                    line_lower = line_stripped.lower()
                    if not any(bp in line_lower for bp in boilerplate):
                        candidates.append((len(line_stripped), line_stripped))
            
            # Sort by length descending, take top 5
            candidates.sort(reverse=True)
            for _, line in candidates[:5]:
                if line not in used_lines:
                    items.append(line[:150])
                    used_lines.add(line)
                    if len(items) >= 5:
                        break
        
        return items[:10]
    
    def extract_meeting_facts(self, parsed: ParsedDoc) -> Dict:
        """Extract key meeting facts from parsed text."""
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
            (r'\d{4}-\d{2}-\d{2}', 'iso_date'),
        ]
        
        time_pattern = r'\d{1,2}:\d{2}\s*(AM|PM|am|pm|a\.m\.|p\.m\.)'
        
        committee_patterns = [
            r'(board\s+of\s+\w+)',
            r'(city\s+council)',
            r'(planning\s+commission)',
            r'(committee\s+on\s+\w+)',
            r'(metro\s+board)',
            r'(board\s+of\s+supervisors)',
        ]
        
        location_keywords = ['location:', 'address:', 'zoom:', 'meeting location', 
                            'board room', 'city hall', 'chambers', 'room']
        
        for line in lines[:400]:
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) < 3:
                continue
            
            line_lower = line_stripped.lower()
            
            # Date extraction
            for pattern, _ in date_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match and facts['meeting_date'] == 'NOT FOUND':
                    facts['meeting_date'] = match.group(0)
                    break
            
            # Time extraction
            time_match = re.search(time_pattern, line_stripped, re.IGNORECASE)
            if time_match and facts['meeting_time'] == 'NOT FOUND':
                facts['meeting_time'] = time_match.group(0)
            
            # Committee extraction
            for pattern in committee_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match and facts['committee'] == 'NOT FOUND':
                    facts['committee'] = match.group(0).title()
                    break
            
            # Location extraction
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
        
        # Extract agenda items using 4-tier method
        facts['agenda_items'] = self.extract_agenda_items_4tier(text)
        
        return facts
