#!/usr/bin/env python3
"""
Production Parser - Robust HTML/PDF text extraction with fallbacks
"""

import hashlib
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class ParsedDoc:
    """Result of parsing a document."""
    text: str
    page_count: int = 0
    parse_warnings: List[str] = None
    confidence: float = 0.0
    fingerprint: str = ""
    
    def __post_init__(self):
        if self.parse_warnings is None:
            self.parse_warnings = []
        # Calculate fingerprint if not provided
        if not self.fingerprint and self.text:
            normalized = self._normalize_for_fingerprint(self.text)
            self.fingerprint = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def _normalize_for_fingerprint(text: str) -> str:
        """Normalize text for stable fingerprinting."""
        # Lowercase, remove extra whitespace, sort lines
        lines = text.lower().split('\n')
        lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
        lines = sorted([l for l in lines if len(l) > 3])
        return '\n'.join(lines)


class ProductionParser:
    """Robust parser for HTML and PDF documents."""
    
    # Minimum confidence threshold to accept parse
    MIN_CONFIDENCE = 0.3
    
    # Minimum text length to consider successful
    MIN_TEXT_LENGTH = 100
    
    def __init__(self):
        self.pdf_available = self._check_pdf_support()
    
    def _check_pdf_support(self) -> bool:
        """Check if PDF extraction is available."""
        try:
            # Try PyPDF2 first (lightweight, pure Python)
            import PyPDF2
            return True
        except ImportError:
            try:
                # Fallback to pdfplumber
                import pdfplumber
                return True
            except ImportError:
                logger.warning("PDF libraries not available. PDF parsing disabled.")
                return False
    
    def parse(self, content: bytes, content_type: str, url: str, source_id: str) -> ParsedDoc:
        """
        Parse content based on type.
        
        Returns ParsedDoc with extracted text, confidence score, and fingerprint.
        """
        content_type = content_type.lower()
        
        if 'html' in content_type or url.endswith('.html') or url.endswith('.htm'):
            return self._parse_html(content, source_id)
        elif 'pdf' in content_type or url.endswith('.pdf'):
            return self._parse_pdf(content, source_id)
        elif 'text' in content_type:
            return self._parse_text(content, source_id)
        else:
            # Try HTML first, then plain text
            try:
                return self._parse_html(content, source_id)
            except:
                return self._parse_text(content, source_id)
    
    def _parse_html(self, content: bytes, source_id: str) -> ParsedDoc:
        """Parse HTML with layout-aware extraction."""
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
            # Fallback: strip all tags
            text = re.sub(r'<[^>]+>', ' ', text)
            warnings.append("no_main_element_found")
        
        # Normalize
        text = self._normalize_text(text)
        
        # Calculate confidence
        confidence = self._calculate_html_confidence(text, warnings)
        
        # Check for empty/low-quality parse
        if len(text) < self.MIN_TEXT_LENGTH:
            warnings.append(f"short_parse:{len(text)}chars")
            confidence = min(confidence, 0.2)
        
        return ParsedDoc(
            text=text,
            page_count=1,  # HTML is single "page"
            parse_warnings=warnings,
            confidence=confidence
        )
    
    def _extract_main_content(self, html: str) -> Optional[str]:
        """Extract main content area from HTML."""
        # Try common content containers
        patterns = [
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*main[^"\']*["\'][^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                # Take the largest match
                largest = max(matches, key=len)
                if len(largest) > 500:  # Must be substantial
                    return largest
        
        return None
    
    def _parse_pdf(self, content: bytes, source_id: str) -> ParsedDoc:
        """Parse PDF with fallback methods."""
        warnings = []
        text = ""
        page_count = 0
        
        if not self.pdf_available:
            warnings.append("pdf_library_not_available")
            return ParsedDoc(
                text="",
                page_count=0,
                parse_warnings=warnings,
                confidence=0.0
            )
        
        # Try PyPDF2 first
        try:
            import PyPDF2
            from io import BytesIO
            
            reader = PyPDF2.PdfReader(BytesIO(content))
            page_count = len(reader.pages)
            
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    warnings.append(f"page_extraction_error:{e}")
            
        except Exception as e:
            warnings.append(f"pypdf2_error:{e}")
            
            # Try pdfplumber fallback
            try:
                import pdfplumber
                from io import BytesIO
                
                with pdfplumber.open(BytesIO(content)) as pdf:
                    page_count = len(pdf.pages)
                    for page in pdf.pages:
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        except:
                            pass
                            
            except Exception as e2:
                warnings.append(f"pdfplumber_error:{e2}")
        
        # Normalize
        text = self._normalize_text(text)
        
        # Check if likely scanned PDF
        if len(text) < 100 and page_count > 0:
            warnings.append("likely_scanned_pdf")
        
        # Strip PDF artifacts
        text = self._strip_pdf_artifacts(text)
        
        # Calculate confidence
        confidence = self._calculate_pdf_confidence(text, page_count, warnings)
        
        return ParsedDoc(
            text=text,
            page_count=page_count,
            parse_warnings=warnings,
            confidence=confidence
        )
    
    def _strip_pdf_artifacts(self, text: str) -> str:
        """Remove common PDF header/footer noise."""
        lines = text.split('\n')
        cleaned = []
        
        for line in lines:
            # Skip page numbers
            if re.match(r'^\s*\d+\s*$', line):
                continue
            # Skip "Page X of Y"
            if re.match(r'(?i)^\s*page\s+\d+\s+of\s+\d+\s*$', line):
                continue
            # Skip repeated headers (common in agendas)
            if len(line) < 50 and re.match(r'(?i)^(city\s+of|agenda|meeting|date:|time:)', line):
                # Keep first occurrence, skip repeats
                if line not in cleaned[-3:] if cleaned else True:
                    pass  # Keep it
                else:
                    continue
            
            cleaned.append(line)
        
        return '\n'.join(cleaned)
    
    def _parse_text(self, content: bytes, source_id: str) -> ParsedDoc:
        """Parse plain text."""
        try:
            text = content.decode('utf-8', errors='replace')
        except:
            text = content.decode('latin-1', errors='replace')
        
        text = self._normalize_text(text)
        
        return ParsedDoc(
            text=text,
            page_count=1,
            parse_warnings=[],
            confidence=0.8 if len(text) > 200 else 0.5
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize extracted text."""
        # Fix Unicode issues
        text = text.replace('\xa0', ' ')  # Non-breaking space
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '-')  # Em dash
        text = text.replace('\u2018', "'")  # Smart quotes
        text = text.replace('\u2019', "'")
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        
        # Fix hyphenation
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def _calculate_html_confidence(self, text: str, warnings: List[str]) -> float:
        """Calculate confidence score for HTML parse."""
        score = 0.7  # Base score
        
        # Length bonus
        if len(text) > 1000:
            score += 0.2
        elif len(text) > 500:
            score += 0.1
        elif len(text) < 200:
            score -= 0.3
        
        # Warning penalties
        score -= len(warnings) * 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_pdf_confidence(self, text: str, page_count: int, warnings: List[str]) -> float:
        """Calculate confidence score for PDF parse."""
        score = 0.6  # Base score
        
        if page_count == 0:
            return 0.0
        
        # Text density
        avg_chars_per_page = len(text) / page_count if page_count > 0 else 0
        if avg_chars_per_page > 1000:
            score += 0.3
        elif avg_chars_per_page > 500:
            score += 0.2
        elif avg_chars_per_page < 100:
            score -= 0.3
        
        # Warning penalties
        if "likely_scanned_pdf" in warnings:
            score -= 0.4
        score -= len([w for w in warnings if not w.startswith("page_")]) * 0.1
        
        return max(0.0, min(1.0, score))
    
    def is_valid_parse(self, doc: ParsedDoc) -> bool:
        """Check if parse result is valid/usable."""
        if doc.confidence < self.MIN_CONFIDENCE:
            return False
        if len(doc.text) < self.MIN_TEXT_LENGTH:
            return False
        return True


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    parser = ProductionParser()
    
    # Test HTML
    html = b"<html><body><main><h1>Test</h1><p>This is test content.</p></main></body></html>"
    result = parser.parse(html, 'text/html', 'http://test.com', 'test')
    print(f"HTML parse: {len(result.text)} chars, confidence: {result.confidence}")
    print(f"Fingerprint: {result.fingerprint}")
