"""Main FASTMCP server implementation."""

import logging
import os
import signal
import sys
from typing import Dict

from fastmcp import FastMCP

from .cache import CacheManager
from .history import DomainHistoryChecker
from .validators import URLValidator, ValidationLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("URL Reputation Checker")

# Global instances
cache_manager = CacheManager(os.getenv("REDIS_URL", "redis://localhost:6379"))
history_checker = DomainHistoryChecker()


@mcp.tool()
async def check_url_reputation(url: str) -> Dict:
    """
    Check reputation for a single URL.

    Args:
        url: URL to validate and check reputation

    Returns:
        Dictionary containing:
        - url: The original URL
        - is_valid: Whether the URL exists and returns content
        - reputation_score: 0-100 score
        - domain_age_days: Age of the domain
        - first_seen_date: Earliest known appearance
        - warnings: List of potential issues
        - confidence_level: "high", "medium", or "low"
        - error: Error message if operation failed
    """
    try:
        # Check cache first
        cached = await cache_manager.get_validation_result(url)
        if cached:
            logger.info(f"Returning cached result for {url}")
            return cached

        # Validate URL
        async with URLValidator() as validator:
            validation_result = await validator.check_url(
                url, ValidationLevel.COMPREHENSIVE
            )

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

        return result_dict

    except Exception as e:
        logger.error(f"Error checking URL reputation for {url}: {str(e)}")
        return {
            "url": url,
            "is_valid": False,
            "status_code": 0,
            "response_time_ms": 0,
            "reputation_score": 0,
            "domain_age_days": None,
            "first_seen_date": None,
            "wayback_snapshots": 0,
            "warnings": [],
            "confidence_level": "low",
            "error": f"Failed to check URL: {str(e)}",
        }


def signal_handler(sig, frame):
    """Handle graceful shutdown."""
    logger.info("Shutting down server...")
    sys.exit(0)


if __name__ == "__main__":
    # Handle graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Starting URL Reputation Checker server...")
        # Run the server
        mcp.run()
    except Exception as e:
        # Ignore BrokenResourceError during shutdown
        if "BrokenResourceError" not in str(type(e).__name__):
            logger.error(f"Server error: {str(e)}")
            raise
