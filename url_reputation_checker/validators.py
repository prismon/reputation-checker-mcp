"""Core validation logic for URLs."""

import asyncio
import re
import ssl
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import certifi
import httpx
import validators
from bs4 import BeautifulSoup

from .models import URLValidationResult, ConfidenceLevel, ValidationLevel


class URLValidator:
    """Handles URL validation and basic checks."""
    
    def __init__(self, timeout: float = 10.0, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.user_agent = user_agent or "URL-Reputation-Checker/1.0"
        self.client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            verify=certifi.where(),
            headers={"User-Agent": self.user_agent}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL has valid format."""
        return validators.url(url) is True
    
    async def check_url(self, url: str, level: ValidationLevel = ValidationLevel.STANDARD) -> URLValidationResult:
        """Validate a single URL."""
        if not self.is_valid_url(url):
            return URLValidationResult(
                url=url,
                is_valid=False,
                status_code=0,
                response_time=0,
                content_length=0,
                ssl_valid=False,
                warnings=["Invalid URL format"],
                confidence_level=ConfidenceLevel.HIGH
            )
        
        start_time = time.time()
        warnings = []
        
        try:
            response = await self.client.get(url)
            response_time = time.time() - start_time
            
            # Basic validation
            is_valid = response.status_code in [200, 201, 202, 203, 204, 301, 302, 307, 308]
            content_length = len(response.content)
            
            # SSL validation
            ssl_valid = url.startswith("https://")
            if ssl_valid and level != ValidationLevel.BASIC:
                ssl_valid = await self._validate_ssl(url)
            
            # Content validation for standard and comprehensive levels
            if level != ValidationLevel.BASIC and response.status_code == 200:
                content_warnings = self._validate_content(response.text, response.headers)
                warnings.extend(content_warnings)
            
            # Check for suspicious patterns
            if level == ValidationLevel.COMPREHENSIVE:
                pattern_warnings = self._check_suspicious_patterns(url, response.text)
                warnings.extend(pattern_warnings)
            
            return URLValidationResult(
                url=url,
                is_valid=is_valid,
                status_code=response.status_code,
                response_time=response_time,
                content_length=content_length,
                ssl_valid=ssl_valid,
                warnings=warnings,
                confidence_level=self._determine_confidence(is_valid, warnings),
                metadata={
                    "final_url": str(response.url),
                    "redirect_count": len(response.history),
                    "content_type": response.headers.get("content-type", "unknown")
                }
            )
            
        except httpx.TimeoutException:
            return URLValidationResult(
                url=url,
                is_valid=False,
                status_code=0,
                response_time=self.timeout,
                content_length=0,
                ssl_valid=False,
                warnings=["Request timeout"],
                confidence_level=ConfidenceLevel.HIGH
            )
        except Exception as e:
            return URLValidationResult(
                url=url,
                is_valid=False,
                status_code=0,
                response_time=time.time() - start_time,
                content_length=0,
                ssl_valid=False,
                warnings=[f"Request failed: {str(e)}"],
                confidence_level=ConfidenceLevel.HIGH
            )
    
    async def _validate_ssl(self, url: str) -> bool:
        """Validate SSL certificate."""
        try:
            parsed = urlparse(url)
            context = ssl.create_default_context(cafile=certifi.where())
            
            reader, writer = await asyncio.open_connection(
                parsed.hostname, 
                parsed.port or 443,
                ssl=context
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    def _validate_content(self, content: str, headers: Dict) -> List[str]:
        """Validate page content for suspicious indicators."""
        warnings = []
        
        # Check content length
        if len(content) < 100:
            warnings.append("Very short content - possible placeholder page")
        
        # Check for parking page indicators
        parking_indicators = [
            "domain for sale",
            "this domain is parked",
            "buy this domain",
            "domain parking",
            "under construction",
            "coming soon"
        ]
        
        content_lower = content.lower()
        for indicator in parking_indicators:
            if indicator in content_lower:
                warnings.append(f"Possible parking page: '{indicator}' found")
                break
        
        # Check for valid HTML structure
        try:
            soup = BeautifulSoup(content, 'html.parser')
            if not soup.find('html') or not soup.find('body'):
                warnings.append("Invalid HTML structure")
        except:
            if headers.get("content-type", "").startswith("text/html"):
                warnings.append("Failed to parse HTML")
        
        return warnings
    
    def _check_suspicious_patterns(self, url: str, content: str) -> List[str]:
        """Check for patterns common in AI-hallucinated URLs."""
        warnings = []
        
        # Check URL patterns
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Common AI hallucination patterns
        suspicious_patterns = [
            r'/blog/\d{4}/\d{2}/\d{2}/[a-z-]+',  # Overly specific blog paths
            r'/docs/v\d+\.\d+\.\d+/api',  # Version-specific API docs
            r'/research/papers/\d{4}/',  # Academic paper patterns
            r'/products/[a-z]+-[a-z]+-[a-z]+-[a-z]+',  # Over-hyphenated product names
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, path):
                warnings.append(f"URL pattern commonly seen in AI hallucinations")
                break
        
        # Check for excessive path depth
        path_parts = [p for p in path.split('/') if p]
        if len(path_parts) > 6:
            warnings.append("Unusually deep URL path structure")
        
        # Check domain name patterns
        domain = parsed.hostname
        if domain:
            # Check for excessive subdomains
            if domain.count('.') > 3:
                warnings.append("Excessive subdomains")
            
            # Check for typosquatting patterns
            common_domains = ['github.com', 'google.com', 'microsoft.com', 'amazon.com']
            for common in common_domains:
                if self._is_typosquatting(domain, common):
                    warnings.append(f"Possible typosquatting of {common}")
        
        return warnings
    
    def _is_typosquatting(self, domain: str, target: str) -> bool:
        """Check if domain might be typosquatting a target domain."""
        # Simple Levenshtein distance check
        if domain == target:
            return False
        
        # Remove TLD for comparison
        domain_base = domain.split('.')[0]
        target_base = target.split('.')[0]
        
        # Calculate similarity
        distance = self._levenshtein_distance(domain_base, target_base)
        
        # If very similar but not identical, might be typosquatting
        return 0 < distance <= 2
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _determine_confidence(self, is_valid: bool, warnings: List[str]) -> ConfidenceLevel:
        """Determine confidence level based on validation results."""
        if not is_valid:
            return ConfidenceLevel.HIGH
        
        warning_count = len(warnings)
        if warning_count == 0:
            return ConfidenceLevel.HIGH
        elif warning_count <= 2:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW