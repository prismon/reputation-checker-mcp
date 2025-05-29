"""Domain history and reputation checking."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

import tldextract
import waybackpy
import whois

from .models import DomainHistory, URLValidationResult


class DomainHistoryChecker:
    """Check domain history using various sources."""

    def __init__(self, user_agent: str = "URL-Reputation-Checker/1.0"):
        self.user_agent = user_agent

    async def get_domain_history(self, url: str) -> DomainHistory:
        """Get comprehensive domain history."""
        # Extract domain from URL
        extracted = tldextract.extract(url)
        domain = f"{extracted.domain}.{extracted.suffix}"

        # Run all checks concurrently
        results = await asyncio.gather(
            self._get_whois_info(domain),
            self._get_wayback_info(url),
            return_exceptions=True,
        )

        whois_info = results[0] if not isinstance(results[0], Exception) else {}
        wayback_info = results[1] if not isinstance(results[1], Exception) else {}

        # Calculate domain age
        creation_date = whois_info.get("creation_date")
        age_days = None
        if creation_date:
            age_days = (datetime.now(timezone.utc) - creation_date).days

        return DomainHistory(
            domain=domain,
            creation_date=creation_date,
            expiration_date=whois_info.get("expiration_date"),
            registrar=whois_info.get("registrar"),
            wayback_first_snapshot=wayback_info.get("first_snapshot"),
            wayback_total_snapshots=wayback_info.get("total_snapshots", 0),
            age_days=age_days,
        )

    async def _get_whois_info(self, domain: str) -> Dict[str, Any]:
        """Get WHOIS information for a domain."""
        try:
            # Run WHOIS lookup in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            w = await loop.run_in_executor(None, whois.whois, domain)

            result = {}

            # Handle creation date
            if hasattr(w, "creation_date"):
                creation_date = w.creation_date
                if isinstance(creation_date, list):
                    creation_date = creation_date[0]
                if creation_date:
                    result["creation_date"] = self._ensure_timezone(creation_date)

            # Handle expiration date
            if hasattr(w, "expiration_date"):
                expiration_date = w.expiration_date
                if isinstance(expiration_date, list):
                    expiration_date = expiration_date[0]
                if expiration_date:
                    result["expiration_date"] = self._ensure_timezone(expiration_date)

            # Get registrar
            if hasattr(w, "registrar"):
                result["registrar"] = w.registrar

            return result

        except Exception:
            # WHOIS lookup can fail for many reasons
            return {}

    async def _get_wayback_info(self, url: str) -> Dict[str, Any]:
        """Get Wayback Machine information."""
        try:
            # Create Wayback object
            loop = asyncio.get_event_loop()

            def get_wayback_data():
                wb = waybackpy.Url(url, self.user_agent)

                # Get oldest archive
                try:
                    oldest = wb.oldest()
                    oldest_date = None
                    if oldest and hasattr(oldest, "timestamp"):
                        # Parse wayback timestamp (YYYYMMDDHHMMSS)
                        ts = str(oldest.timestamp)
                        if len(ts) >= 8:
                            year = ts[0:4]
                            month = ts[4:6]
                            day = ts[6:8]
                            oldest_date = datetime(
                                int(year), int(month), int(day), tzinfo=timezone.utc
                            )
                except Exception:
                    oldest_date = None

                # Get total number of snapshots
                try:
                    cdx = wb.cdx_api()
                    total = len(list(cdx))
                except Exception:
                    total = 0

                return {"first_snapshot": oldest_date, "total_snapshots": total}

            # Run in executor to avoid blocking
            result = await loop.run_in_executor(None, get_wayback_data)
            return result

        except Exception:
            return {}

    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime has timezone information."""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def calculate_reputation_score(
        self, domain_history: DomainHistory, validation_result: URLValidationResult
    ) -> float:
        """
        Calculate reputation score based on multiple factors.

        Scoring breakdown:
        - Domain age: 0-30 points
        - Wayback presence: 0-20 points
        - Technical factors: 0-25 points
        - Consistency: 0-25 points
        """
        score = 0.0

        # Domain age score (0-30 points)
        if domain_history.age_days:
            if domain_history.age_days >= 365 * 5:  # 5+ years
                score += 30
            elif domain_history.age_days >= 365 * 2:  # 2-5 years
                score += 20
            elif domain_history.age_days >= 365:  # 1-2 years
                score += 15
            elif domain_history.age_days >= 180:  # 6-12 months
                score += 10
            elif domain_history.age_days >= 90:  # 3-6 months
                score += 5
            else:  # Less than 3 months
                score += 2

        # Wayback Machine presence (0-20 points)
        if domain_history.wayback_total_snapshots > 0:
            if domain_history.wayback_total_snapshots >= 100:
                score += 20
            elif domain_history.wayback_total_snapshots >= 50:
                score += 15
            elif domain_history.wayback_total_snapshots >= 20:
                score += 10
            elif domain_history.wayback_total_snapshots >= 5:
                score += 5
            else:
                score += 2

        # Technical factors (0-25 points)
        if validation_result.ssl_valid:
            score += 10

        if validation_result.response_time < 1.0:
            score += 10
        elif validation_result.response_time < 2.0:
            score += 5

        if validation_result.status_code == 200:
            score += 5

        # Consistency factors (0-25 points)
        if len(validation_result.warnings) == 0:
            score += 25
        elif len(validation_result.warnings) == 1:
            score += 15
        elif len(validation_result.warnings) == 2:
            score += 10
        elif len(validation_result.warnings) == 3:
            score += 5

        return min(score, 100.0)  # Cap at 100
