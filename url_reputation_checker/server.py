"""Main FASTMCP server implementation."""

import asyncio
import os
from typing import Dict, List, Optional
from datetime import datetime

from fastmcp import FastMCP

from .validators import URLValidator, ValidationLevel
from .extractors import LinkExtractor
from .history import DomainHistoryChecker
from .cache import CacheManager
from .models import (
    URLValidationResult, 
    LinkExtractionResult,
    ConfidenceLevel
)


# Initialize FastMCP server
mcp = FastMCP("URL Reputation Checker")

# Global instances
cache_manager = CacheManager(os.getenv("REDIS_URL", "redis://localhost:6379"))
extractor = LinkExtractor()
history_checker = DomainHistoryChecker()

# Track validation results for reporting
validation_history = []


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
    results = []
    
    async with URLValidator() as validator:
        for url in urls:
            # Check cache first
            cached = await cache_manager.get_validation_result(url)
            if cached:
                results.append(cached)
                continue
            
            # Validate URL
            validation_result = await validator.check_url(url, ValidationLevel.COMPREHENSIVE)
            
            # Get domain history
            domain_history = await history_checker.get_domain_history(url)
            
            # Calculate reputation score
            reputation_score = history_checker.calculate_reputation_score(
                domain_history, validation_result
            )
            
            # Update validation result with reputation info
            validation_result.reputation_score = reputation_score
            validation_result.domain_age_days = domain_history.age_days
            validation_result.first_seen_date = domain_history.wayback_first_snapshot
            validation_result.wayback_snapshots = domain_history.wayback_total_snapshots
            
            # Convert to dict
            result_dict = validation_result.to_dict()
            
            # Cache the result
            await cache_manager.set_validation_result(
                url, result_dict, validation_result.is_valid
            )
            
            # Track in history
            validation_history.append(result_dict)
            
            results.append(result_dict)
    
    return results


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
    # Extract links
    extracted_links = extractor.extract_links(content, content_type)
    
    if not extracted_links:
        return {
            "extracted_links": [],
            "valid_links": [],
            "invalid_links": [],
            "summary": {
                "total_links": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "average_reputation_score": 0,
                "recommendation": "No links found in content"
            }
        }
    
    # Check reputation for all extracted links
    reputation_results = await check_links_reputation(extracted_links)
    
    # Separate valid and invalid links
    valid_links = []
    invalid_links = []
    total_reputation_score = 0
    
    for result in reputation_results:
        if result['is_valid']:
            valid_links.append(result)
            total_reputation_score += result['reputation_score']
        else:
            invalid_links.append(result['url'])
    
    # Calculate average reputation
    avg_reputation = (
        total_reputation_score / len(valid_links) 
        if valid_links else 0
    )
    
    # Create result
    extraction_result = LinkExtractionResult(
        extracted_links=extracted_links,
        valid_links=[URLValidationResult(**{
            k: v for k, v in link.items() 
            if k != 'first_seen_date'
        }) for link in valid_links],
        invalid_links=invalid_links,
        total_links=len(extracted_links),
        valid_count=len(valid_links),
        invalid_count=len(invalid_links),
        average_reputation_score=avg_reputation
    )
    
    return extraction_result.to_dict()


@mcp.tool()
async def validate_url(url: str) -> Dict:
    """
    Validate a single URL and return detailed information.
    
    Args:
        url: The URL to validate
        
    Returns:
        Detailed validation information including status, response time, and warnings
    """
    async with URLValidator() as validator:
        result = await validator.check_url(url, ValidationLevel.STANDARD)
        return result.to_dict()


@mcp.tool()
async def get_domain_history(domain: str) -> Dict:
    """
    Get historical information about a domain.
    
    Args:
        domain: Domain name or URL to check
        
    Returns:
        Domain history including creation date, wayback data, and age
    """
    # Check cache first
    cached = await cache_manager.get_domain_history(domain)
    if cached:
        return cached
    
    # Get domain history
    history = await history_checker.get_domain_history(domain)
    result = history.to_dict()
    
    # Cache the result
    await cache_manager.set_domain_history(domain, result)
    
    return result


@mcp.resource("url_validation_report")
async def get_validation_report() -> str:
    """Return a formatted report of all validated URLs."""
    if not validation_history:
        return "No URLs have been validated yet."
    
    report = f"# URL Validation Report\n\n"
    report += f"Generated: {datetime.utcnow().isoformat()}Z\n"
    report += f"Total URLs validated: {len(validation_history)}\n\n"
    
    # Summary statistics
    valid_count = sum(1 for r in validation_history if r['is_valid'])
    invalid_count = len(validation_history) - valid_count
    avg_reputation = sum(r['reputation_score'] for r in validation_history) / len(validation_history)
    
    report += f"## Summary\n"
    report += f"- Valid URLs: {valid_count}\n"
    report += f"- Invalid URLs: {invalid_count}\n"
    report += f"- Average reputation score: {avg_reputation:.1f}/100\n\n"
    
    # Detailed results
    report += "## Detailed Results\n\n"
    for result in validation_history[-50:]:  # Last 50 results
        status = "✓" if result['is_valid'] else "✗"
        report += f"{status} **{result['url']}**\n"
        report += f"  - Status: {result['status_code']}\n"
        report += f"  - Reputation: {result['reputation_score']:.1f}/100\n"
        if result['warnings']:
            report += f"  - Warnings: {', '.join(result['warnings'])}\n"
        report += "\n"
    
    return report


@mcp.resource("cache_stats")
async def get_cache_stats() -> Dict:
    """Get cache statistics."""
    return await cache_manager.get_stats()


# Server lifecycle hooks
@mcp.server.on_start()
async def on_start():
    """Initialize server resources."""
    await cache_manager.connect()
    print("URL Reputation Checker started successfully")


@mcp.server.on_stop()
async def on_stop():
    """Cleanup server resources."""
    await cache_manager.disconnect()
    print("URL Reputation Checker stopped")


if __name__ == "__main__":
    # Run the server
    mcp.run()