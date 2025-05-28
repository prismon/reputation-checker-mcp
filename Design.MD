# URL Reputation and Validity Checker - Design Document

## Project Overview

A Python-based MCP (Model Context Protocol) server using FASTMCP 2.0 that validates URLs and provides reputation information. This tool helps verify that URLs are not AI hallucinations and provides historical context about web pages.

## Core Objectives

1. **URL Validation**: Verify that URLs resolve to actual web pages
2. **Content Verification**: Ensure pages return valid content (not 404s, parking pages, etc.)
3. **Historical Analysis**: Determine how long pages/domains have existed
4. **Reputation Scoring**: Provide confidence metrics about URL reliability

## Architecture

### FASTMCP Server Structure

```python
from fastmcp import FastMCP
from typing import List, Dict, Optional
from datetime import datetime

mcp = FastMCP("URL Reputation Checker")

@mcp.tool()
async def check_links_reputation(urls: List[str]) -> List[Dict]:
    """
    Check reputation for a list of URLs.
    
    Args:
        urls: List of URLs to validate and check reputation
        
    Returns:
        List of dictionaries containing:
        - url: The original URL
        - is_valid: Whether the URL exists and returns content
        - reputation_score: 0-100 score
        - domain_age_days: Age of the domain
        - first_seen_date: Earliest known appearance
        - warnings: List of potential issues
        - confidence_level: "high", "medium", or "low"
    """
    pass

@mcp.tool()
async def extract_and_check_links(content: str, content_type: str = "auto") -> Dict:
    """
    Extract links from HTML or text content and check their reputation.
    
    Args:
        content: HTML or plain text content containing URLs
        content_type: "html", "text", or "auto" (auto-detect)
        
    Returns:
        Dictionary containing:
        - extracted_links: List of all URLs found
        - valid_links: List of validated URLs with reputation info
        - invalid_links: List of URLs that failed validation
        - summary: Overall statistics and recommendations
    """
    pass

@mcp.tool()
async def validate_url(url: str) -> Dict:
    """Validate a single URL and return detailed information"""
    pass

@mcp.tool()
async def get_domain_history(domain: str) -> Dict:
    """Get historical information about a domain"""
    pass

@mcp.resource("url_validation_report")
async def get_validation_report() -> str:
    """Return a formatted report of all validated URLs"""
    pass
```

## Core Functionality

### 1. URL Validation

**Implementation Approach:**
- **HTTP/HTTPS Verification**: Check response codes (200, 301, 302 = valid)
- **Content Verification**: Analyze response body for:
  - Minimum content length
  - Valid HTML structure
  - Absence of parking page indicators
  - SSL certificate validation
- **Response Time**: Track load times as reliability indicator

**Validation Levels:**
1. **Basic**: URL resolves and returns 200 OK
2. **Standard**: Basic + content verification
3. **Comprehensive**: Standard + SSL check + content analysis

### 2. Historical Analysis

**Primary Approaches:**

1. **Wayback Machine API**
   - Query Internet Archive for earliest snapshot
   - Track frequency of archiving (indicates importance)
   - Compare current content with historical versions

2. **Domain Registration Data (WHOIS)**
   - Domain creation date
   - Registration history
   - Registrar information

3. **SSL Certificate History**
   - Certificate issuance dates
   - Certificate transparency logs

4. **Search Engine Cache**
   - Google cache timestamps
   - Bing indexed date
   - First appearance in search results

### 3. Reputation Scoring

**Scoring Factors:**
- **Age Score** (0-30 points): Older = more trustworthy
- **Consistency Score** (0-25 points): Stable content over time
- **Technical Score** (0-25 points): SSL, proper headers, fast response
- **Archive Score** (0-20 points): Frequency in web archives

**Total Score**: 0-100 (Higher = more reputable)

## Alternative Approaches & Enhancements

### 1. Content Fingerprinting
- Generate content hashes to detect AI-generated patterns
- Compare against known AI content signatures
- Detect templated/generated content

### 2. Cross-Reference Validation
- Check if URL is referenced by reputable sources
- Verify backlinks from established sites
- Social media mention analysis

### 3. AI Hallucination Detection
- **Pattern Analysis**: Common AI URL patterns (e.g., plausible but non-existent paths)
- **Domain Typosquatting**: Check for slight variations of legitimate domains
- **Path Structure**: Verify realistic URL structures

### 4. Real-time Monitoring
- Periodic re-validation of previously checked URLs
- Alert system for URL status changes
- Historical tracking database

## Additional Considerations

### Security & Privacy
1. **Request Headers**: Use appropriate user-agent strings
2. **Rate Limiting**: Respect robots.txt and implement delays
3. **Data Storage**: Secure storage of validation results
4. **VPN/Proxy Support**: For geo-restricted content

### Performance Optimizations
1. **Caching Strategy**:
   - Cache validation results (TTL: 24 hours for valid, 1 hour for invalid)
   - Cache domain history (TTL: 7 days)
   
2. **Parallel Processing**:
   - Async HTTP requests
   - Batch processing for multiple URLs
   - Connection pooling

### Error Handling
1. **Network Errors**: Retry logic with exponential backoff
2. **Timeout Handling**: Configurable timeouts (default: 10s)
3. **Invalid URLs**: Graceful handling with detailed error messages

### Extended Features
1. **Screenshot Capture**: Visual proof of page existence
2. **Content Extraction**: Key metadata (title, description, publish date)
3. **Redirect Chain Analysis**: Track full redirect path
4. **Geographic Validation**: Check URL accessibility from multiple regions

## Data Schema

```python
class URLValidationResult:
    url: str
    is_valid: bool
    status_code: int
    response_time: float
    content_length: int
    ssl_valid: bool
    domain_age_days: Optional[int]
    first_seen_date: Optional[datetime]
    wayback_snapshots: int
    reputation_score: float
    confidence_level: str  # "high", "medium", "low"
    warnings: List[str]
    metadata: Dict[str, any]
```

## Implementation Phases

### Phase 1: Core Validation (Week 1)
- Basic URL validation
- HTTP/HTTPS checking
- Response analysis

### Phase 2: Historical Features (Week 2)
- Wayback Machine integration
- WHOIS lookup
- Basic reputation scoring

### Phase 3: Advanced Detection (Week 3)
- AI hallucination patterns
- Content fingerprinting
- Cross-reference validation

### Phase 4: Production Features (Week 4)
- Caching system
- Batch processing
- MCP client examples

## Testing Strategy

1. **Unit Tests**: Individual validation functions
2. **Integration Tests**: External API interactions
3. **Performance Tests**: Batch processing capabilities
4. **Edge Cases**:
   - Redirects chains
   - Geo-blocked content
   - Dynamic/JavaScript-heavy sites
   - Rate-limited APIs

## Dependencies

```toml
[project]
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.25.0",  # Async HTTP client
    "beautifulsoup4>=4.12.0",  # HTML parsing
    "python-whois>=0.8.0",  # WHOIS lookups
    "validators>=0.22.0",  # URL validation
    "redis>=5.0.0",  # Caching
    "waybackpy>=3.0.6",  # Wayback Machine API
]
```

## Success Metrics

1. **Accuracy**: >95% correct URL status identification
2. **Performance**: <2s average validation time per URL
3. **Coverage**: Support for 99% of standard web URLs
4. **Reliability**: <0.1% false positive rate for hallucination detection