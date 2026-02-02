#!/usr/bin/env python3
"""
Enhanced Parser with Document Discovery and PDF Support
"""

import hashlib
import io
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

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


@dataclass
class ParsedDoc:
    """Result of parsing a document."""
    text: str
    page_count: int = 0
    parse_warnings: List[str] = None
    confidence: float = 0.0
    fingerprint: str = ""
    source_url: str = ""
    
    def __post_init__(self):
        if self.parse_warnings is None:
            self.parse_warnings = []
        if not self.fingerprint and self.text:
            normalized = self._normalize_for_fingerprint(self.text)
            self.fingerprint = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def _normalize_for_fingerprint(text: str) -> str:
        """Normalize text for stable fingerprinting."""
        lines = text.lower().split('\n')
        lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
        lines = sorted([l for l in lines if len(l) > 3])
        return '\n'.join(lines)


class AgendaDiscovery:
    """Discovers agenda documents from landing pages."""
    
    # Keywords that suggest an agenda document
    POSITIVE_KEYWORDS = ['agenda', 'packet', 'meeting', 'board', 'commission', 
                        'committee', 'minutes', 'notice', 'hearing', 'council']
    
    # Keywords that suggest non-agenda content
    NEGATIVE_KEYWORDS = ['archive', 'subscribe', 'donate', 'contact', 
                        'login', 'search', 'newsletter', 'rss', 'feed']
    
    # Strong agenda packet indicators
    AGENDA_PACKET_KEYWORDS = ['agenda packet', 'packet', 'materials', 'board materials']
    AGENDA_MEETING_KEYWORDS = ['agenda', 'meeting']
    
    # Date patterns
    DATE_PATTERNS = [
        r'\d{4}',  # Year
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*',  # Month names
        r'\d{1,2}/\d{1,2}',  # MM/DD
        r'\d{1,2}-\d{1,2}',  # MM-DD
    ]
    
    def score_link(self, href: str, anchor_text: str, base_url: str) -> int:
        """
        Score a link based on likelihood of being an agenda document.
        
        Improved scoring rubric:
        +25 for PDF
        +20 for "agenda packet"
        +15 for "agenda" + ("packet" OR "materials" OR "meeting")
        +10 for positive keywords (agenda, meeting, etc.)
        +12 for date-like tokens
        +8 for same domain
        -30 if href filename contains "calendar"
        -15 if anchor text contains "calendar" (and not "agenda")
        -10 for other negative keywords
        """
        score = 0
        href_lower = href.lower()
        text_lower = anchor_text.lower()
        combined = href_lower + ' ' + text_lower
        
        # Get filename from href
        href_filename = href_lower.split('/')[-1].split('?')[0]
        
        # +25 for PDF
        if href_lower.endswith('.pdf'):
            score += 25
        
        # STRONG PENALTY for calendar in filename
        if 'calendar' in href_filename:
            score -= 30
        
        # Penalty for calendar in anchor text (unless it also says agenda)
        if 'calendar' in text_lower and 'agenda' not in text_lower:
            score -= 15
        
        # +20 for "agenda packet"
        if 'agenda packet' in combined:
            score += 20
        
        # +15 for agenda + packet/materials/meeting
        elif 'agenda' in combined:
            if any(kw in combined for kw in ['packet', 'materials', 'meeting']):
                score += 15
            else:
                score += 10  # Just agenda is still good
        
        # +10 for other positive keywords
        for keyword in self.POSITIVE_KEYWORDS:
            if keyword in combined and keyword != 'agenda':  # Already counted above
                score += 10
                break
        
        # +12 for date patterns
        for pattern in self.DATE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                score += 12
                break
        
        # +8 for same domain
        base_domain = urlparse(base_url).netloc
        link_domain = urlparse(urljoin(base_url, href)).netloc
        if base_domain == link_domain or not link_domain:
            score += 8
        
        # -10 for other negative keywords
        for keyword in self.NEGATIVE_KEYWORDS:
            if keyword in combined:
                score -= 10
                break
        
        return score
    
    def extract_links(self, html: str, base_url: str) -> List[Dict]:
        """Extract all links from HTML with their anchor text."""
        links = []
        
        # Find all anchor tags
        pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for href, anchor_html in matches:
            # Clean up anchor text (remove HTML tags)
            anchor_text = re.sub(r'<[^>]+>', ' ', anchor_html).strip()
            anchor_text = re.sub(r'\s+', ' ', anchor_text)
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            
            # Score the link
            score = self.score_link(href, anchor_text, base_url)
            
            links.append({
                'url': absolute_url,
                'href': href,
                'anchor_text': anchor_text[:100],  # Truncate long text
                'score': score
            })
        
        # Sort by score descending
        links.sort(key=lambda x: x['score'], reverse=True)
        return links
    
    def find_best_agenda_link(self, html: str, base_url: str, sanity_check: bool = False, fetcher=None) -> Optional[Dict]:
        """
        Find the best agenda document link from HTML.
        
        If sanity_check=True and fetcher is provided, will validate the document
        isn't a calendar and fall back to next best candidate if it is.
        """
        links = self.extract_links(html, base_url)
        
        if not links:
            return None
        
        # Filter for reasonable candidates (score > -20)
        candidates = [l for l in links if l['score'] > -20]
        
        if not candidates:
            return links[0] if links else None  # Return highest even if negative
        
        if sanity_check and fetcher:
            # Try candidates in order until we find a non-calendar
            for candidate in candidates[:5]:  # Check top 5
                try:
                    content, meta = fetcher.fetch(candidate['url'], 'sanity_check')
                    if content and meta.get('status_code') == 200:
                        # Check if it's a PDF
                        if candidate['url'].lower().endswith('.pdf'):
                            # Parse first page to check for calendar
                            try:
                                import io
                                if pdfplumber:
                                    with pdfplumber.open(io.BytesIO(content)) as pdf:
                                        if len(pdf.pages) > 0:
                                            first_page_text = pdf.pages[0].extract_text() or ""
                                            first_page_lower = first_page_text.lower()
                                            # Reject if calendar and not agenda
                                            if 'calendar' in first_page_lower and 'agenda' not in first_page_lower:
                                                logger.info(f"Rejecting calendar PDF: {candidate['url']}")
                                                continue  # Try next candidate
                                elif PyPDF2:
                                    reader = PyPDF2.PdfReader(io.BytesIO(content))
                                    if len(reader.pages) > 0:
                                        first_page_text = reader.pages[0].extract_text() or ""
                                        first_page_lower = first_page_text.lower()
                                        if 'calendar' in first_page_lower and 'agenda' not in first_page_lower:
                                            logger.info(f"Rejecting calendar PDF: {candidate['url']}")
                                            continue
                            except Exception as e:
                                logger.warning(f"Sanity check failed for {candidate['url']}: {e}")
                        
                        # This candidate passed sanity check
                        return candidate
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch {candidate['url']}: {e}")
                    continue
            
            # If all failed sanity check, return first candidate anyway
            return candidates[0]
        
        # Return highest scored without sanity check
        return candidates[0]


class EnhancedParser:
    """Parser with PDF support and document discovery."""
    
    MIN_CONFIDENCE = 0.3
    MIN_TEXT_LENGTH = 100
    
    def __init__(self):
        self.discovery = AgendaDiscovery()
        self.pdf_available = PDFPLUMBER_AVAILABLE or PYPDF2_AVAILABLE
    
    def parse(self, content: bytes, content_type: str, url: str, source_id: str) -> ParsedDoc:
        """Parse content based on type."""
        content_type = content_type.lower() if content_type else ''
        
        # Detect PDF by content type or extension
        is_pdf = ('pdf' in content_type or 
                  url.lower().endswith('.pdf') or
                  content[:4] == b'%PDF')
        
        if is_pdf:
            return self._parse_pdf(content, url, source_id)
        elif 'html' in content_type or url.endswith(('.html', '.htm')):
            return self._parse_html(content, url, source_id)
        else:
            # Try HTML first, then plain text
            try:
                return self._parse_html(content, url, source_id)
            except:
                return self._parse_text(content, url, source_id)
    
    def _parse_pdf(self, content: bytes, url: str, source_id: str) -> ParsedDoc:
        """Parse PDF document."""
        warnings = []
        text = ""
        page_count = 0
        
        # Try pdfplumber first (better extraction)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    page_count = len(pdf.pages)
                    pages_text = []
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text:
                            pages_text.append(page_text)
                    text = '\n\n'.join(pages_text)
                    
                if len(text) > self.MIN_TEXT_LENGTH:
                    logger.info(f"Parsed PDF with pdfplumber: {page_count} pages, {len(text)} chars")
            except Exception as e:
                warnings.append(f"pdfplumber_error: {e}")
                text = ""  # Reset for fallback
        
        # Fallback to PyPDF2
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
                
                if len(text) > self.MIN_TEXT_LENGTH:
                    logger.info(f"Parsed PDF with PyPDF2: {page_count} pages, {len(text)} chars")
            except Exception as e:
                warnings.append(f"pypdf2_error: {e}")
        
        # Normalize text
        text = self._normalize_text(text)
        
        # Calculate confidence
        confidence = self._calculate_pdf_confidence(text, page_count, warnings)
        
        return ParsedDoc(
            text=text,
            page_count=page_count,
            parse_warnings=warnings,
            confidence=confidence,
            source_url=url
        )
    
    def _parse_html(self, content: bytes, url: str, source_id: str) -> ParsedDoc:
        """Parse HTML document."""
        warnings = []
        
        try:
            text = content.decode('utf-8', errors='replace')
        except:
            text = content.decode('latin-1', errors='replace')
        
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Try to extract main content
        main_content = self._extract_main_content(text)
        if main_content:
            text = main_content
        else:
            text = re.sub(r'<[^>]+>', ' ', text)
            warnings.append("no_main_element_found")
        
        text = self._normalize_text(text)
        confidence = self._calculate_html_confidence(text, warnings)
        
        return ParsedDoc(
            text=text,
            page_count=1,
            parse_warnings=warnings,
            confidence=confidence,
            source_url=url
        )
    
    def _parse_text(self, content: bytes, url: str, source_id: str) -> ParsedDoc:
        """Parse plain text."""
        try:
            text = content.decode('utf-8', errors='replace')
        except:
            text = content.decode('latin-1', errors='replace')
        
        text = self._normalize_text(text)
        
        return ParsedDoc(
            text=text,
            page_count=1,
            confidence=0.5 if len(text) > self.MIN_TEXT_LENGTH else 0.2,
            source_url=url
        )
    
    def _extract_main_content(self, html: str) -> Optional[str]:
        """Extract main content area from HTML."""
        patterns = [
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*main[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*id=["\']content["\'][^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                largest = max(matches, key=len)
                if len(largest) > 500:
                    # Strip tags
                    return re.sub(r'<[^>]+>', ' ', largest)
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for diffing and display."""
        if not text:
            return ""
        
        # Remove page numbers ("Page X of Y")
        text = re.sub(r'\b[Pp]age\s+\d+\s+(of|/)\s+\d+\b', '', text)
        text = re.sub(r'\b[Pp]age\s+\d+\b', '', text)
        
        # Remove timestamps ("Printed on...", "Updated...", "Generated...")
        text = re.sub(r'\b[Pp]rinted\s+(on|at)\s+[^\n]+', '', text)
        text = re.sub(r'\b[Uu]pdated\s+(on|at)?\s*[^\n]+', '', text)
        text = re.sub(r'\b[Gg]enerated\s+(on|at)?\s*[^\n]+', '', text)
        
        # Collapse whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Collapse spaces/tabs
        
        # Strip common headers/footers that repeat
        lines = text.split('\n')
        normalized_lines = []
        seen_patterns = set()
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                normalized_lines.append('')
                continue
            
            # Skip very short repeating lines (likely headers/footers)
            pattern = re.sub(r'\d+', '#', stripped.lower())  # Normalize numbers
            if len(stripped) < 50 and pattern in seen_patterns:
                continue
            
            seen_patterns.add(pattern)
            normalized_lines.append(stripped)
        
        return '\n'.join(normalized_lines).strip()
    
    def _calculate_html_confidence(self, text: str, warnings: List[str]) -> float:
        """Calculate confidence score for HTML parsing."""
        if len(text) < self.MIN_TEXT_LENGTH:
            return 0.1
        
        confidence = 0.5
        
        # Boost for agenda-like content
        agenda_keywords = ['agenda', 'meeting', 'board', 'commission', 'council', 'committee']
        for keyword in agenda_keywords:
            if keyword in text.lower():
                confidence += 0.1
                break
        
        # Boost for date patterns
        if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', text):
            confidence += 0.1
        
        # Penalties
        if "no_main_element_found" in warnings:
            confidence -= 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_pdf_confidence(self, text: str, page_count: int, warnings: List[str]) -> float:
        """Calculate confidence score for PDF parsing."""
        if len(text) < self.MIN_TEXT_LENGTH:
            return 0.1
        
        confidence = 0.6  # PDFs generally more reliable
        
        # Boost for substantial content
        if len(text) > 1000:
            confidence += 0.1
        
        # Boost for multiple pages
        if page_count > 1:
            confidence += 0.1
        
        # Boost for agenda-like content
        agenda_keywords = ['agenda', 'meeting', 'item', 'resolution', 'motion']
        for keyword in agenda_keywords:
            if keyword in text.lower():
                confidence += 0.1
                break
        
        # Penalties for warnings
        confidence -= len(warnings) * 0.05
        
        return min(max(confidence, 0.0), 1.0)
    
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
        
        # Date patterns
        date_patterns = [
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', 'month_day_year'),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', 'abbrev_month'),
            (r'\d{1,2}/\d{1,2}/\d{4}', 'slash_date'),
            (r'\d{1,2}-\d{1,2}-\d{4}', 'dash_date'),
        ]
        
        # Time pattern
        time_pattern = r'\d{1,2}:\d{2}\s*(AM|PM|am|pm|a\.m\.|p\.m\.)'
        
        # Committee patterns
        committee_patterns = [
            r'(board\s+of\s+\w+)',
            r'(city\s+council)',
            r'(planning\s+commission)',
            r'(committee\s+on\s+\w+)',
            r'(metro\s+board)',
        ]
        
        # Location patterns
        location_keywords = ['location:', 'address:', 'zoom:', 'meeting location', 'board room', 'city hall']
        
        for line in lines[:300]:  # Check first 300 lines
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
                    # Extract text after keyword or whole line
                    if ':' in line_stripped:
                        parts = line_stripped.split(':', 1)
                        if len(parts) > 1 and len(parts[1].strip()) > 5:
                            facts['location'] = parts[1].strip()[:120]
                        else:
                            facts['location'] = line_stripped[:120]
                    else:
                        facts['location'] = line_stripped[:120]
                    break
            
            # Agenda items (numbered or bulleted)
            if re.match(r'^\d+[\.\)]\s+', line_stripped) or re.match(r'^[•\-\*]\s+', line_stripped):
                if len(line_stripped) > 20 and len(facts['agenda_items']) < 10:
                    # Clean up the item
                    item = re.sub(r'^[\d•\-\*\.\)]+\s*', '', line_stripped)
                    if len(item) > 15:
                        facts['agenda_items'].append(item[:150])
        
        return facts
