"""Data models for URL reputation checker."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationLevel(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


@dataclass
class URLValidationResult:
    """Result of URL validation and reputation check."""
    
    url: str
    is_valid: bool
    status_code: int
    response_time: float
    content_length: int
    ssl_valid: bool
    domain_age_days: Optional[int] = None
    first_seen_date: Optional[datetime] = None
    wayback_snapshots: int = 0
    reputation_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "is_valid": self.is_valid,
            "status_code": self.status_code,
            "response_time": self.response_time,
            "content_length": self.content_length,
            "ssl_valid": self.ssl_valid,
            "domain_age_days": self.domain_age_days,
            "first_seen_date": self.first_seen_date.isoformat() if self.first_seen_date else None,
            "wayback_snapshots": self.wayback_snapshots,
            "reputation_score": self.reputation_score,
            "confidence_level": self.confidence_level.value,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class DomainHistory:
    """Historical information about a domain."""
    
    domain: str
    creation_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    registrar: Optional[str] = None
    wayback_first_snapshot: Optional[datetime] = None
    wayback_total_snapshots: int = 0
    ssl_first_seen: Optional[datetime] = None
    age_days: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "domain": self.domain,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "registrar": self.registrar,
            "wayback_first_snapshot": self.wayback_first_snapshot.isoformat() if self.wayback_first_snapshot else None,
            "wayback_total_snapshots": self.wayback_total_snapshots,
            "ssl_first_seen": self.ssl_first_seen.isoformat() if self.ssl_first_seen else None,
            "age_days": self.age_days,
        }


@dataclass
class LinkExtractionResult:
    """Result of link extraction from content."""
    
    extracted_links: List[str]
    valid_links: List[URLValidationResult]
    invalid_links: List[str]
    total_links: int
    valid_count: int
    invalid_count: int
    average_reputation_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "extracted_links": self.extracted_links,
            "valid_links": [link.to_dict() for link in self.valid_links],
            "invalid_links": self.invalid_links,
            "summary": {
                "total_links": self.total_links,
                "valid_count": self.valid_count,
                "invalid_count": self.invalid_count,
                "average_reputation_score": self.average_reputation_score,
                "recommendation": self._get_recommendation(),
            }
        }
    
    def _get_recommendation(self) -> str:
        """Generate recommendation based on results."""
        if self.average_reputation_score >= 80:
            return "Links appear highly reputable"
        elif self.average_reputation_score >= 60:
            return "Links have moderate reputation - verify important ones"
        elif self.average_reputation_score >= 40:
            return "Links have low reputation - exercise caution"
        else:
            return "Links appear suspicious - high risk of hallucination"