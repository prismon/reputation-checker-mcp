"""Unit tests for models.py"""

import pytest
from datetime import datetime

from url_reputation_checker.models import (
    ConfidenceLevel, 
    ValidationLevel,
    URLValidationResult,
    DomainHistory,
    LinkExtractionResult
)


class TestConfidenceLevel:
    """Test suite for ConfidenceLevel enum."""

    def test_confidence_levels_exist(self):
        """Test that all confidence levels are defined."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"

    def test_confidence_level_values(self):
        """Test confidence level string values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"


class TestValidationLevel:
    """Test suite for ValidationLevel enum."""

    def test_validation_levels_exist(self):
        """Test that all validation levels are defined."""
        assert ValidationLevel.BASIC == "basic"
        assert ValidationLevel.STANDARD == "standard"
        assert ValidationLevel.COMPREHENSIVE == "comprehensive"

    def test_validation_level_values(self):
        """Test validation level string values."""
        assert ValidationLevel.BASIC.value == "basic"
        assert ValidationLevel.STANDARD.value == "standard"
        assert ValidationLevel.COMPREHENSIVE.value == "comprehensive"


class TestURLValidationResult:
    """Test suite for URLValidationResult model."""

    def test_create_basic_validation_result(self):
        """Test creating a basic URLValidationResult."""
        result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            confidence_level=ConfidenceLevel.HIGH
        )
        
        assert result.url == "https://example.com"
        assert result.is_valid is True
        assert result.status_code == 200
        assert result.response_time == 0.5
        assert result.content_length == 1000
        assert result.ssl_valid is True
        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.wayback_snapshots == 0  # Default value
        assert result.reputation_score == 0.0  # Default value
        assert result.warnings == []  # Default empty list

    def test_create_full_validation_result(self):
        """Test creating a URLValidationResult with all fields."""
        first_seen = datetime(2020, 1, 1)
        result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=12345,
            ssl_valid=True,
            domain_age_days=3650,
            first_seen_date=first_seen,
            wayback_snapshots=5000,
            reputation_score=85.0,
            confidence_level=ConfidenceLevel.HIGH,
            warnings=["Test warning"],
            metadata={"extra": "data"}
        )
        
        assert result.domain_age_days == 3650
        assert result.first_seen_date == first_seen
        assert result.wayback_snapshots == 5000
        assert result.reputation_score == 85.0
        assert result.warnings == ["Test warning"]
        assert result.metadata == {"extra": "data"}

    def test_validation_result_to_dict(self):
        """Test converting URLValidationResult to dictionary."""
        first_seen = datetime(2020, 1, 1)
        result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            first_seen_date=first_seen,
            reputation_score=90.0,
            confidence_level=ConfidenceLevel.HIGH,
            warnings=["Test warning"]
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["is_valid"] is True
        assert data["status_code"] == 200
        assert data["response_time"] == 0.5
        assert data["content_length"] == 1000
        assert data["ssl_valid"] is True
        assert data["first_seen_date"] == first_seen.isoformat()
        assert data["reputation_score"] == 90.0
        assert data["confidence_level"] == "high"
        assert data["warnings"] == ["Test warning"]

    def test_validation_result_to_dict_no_first_seen(self):
        """Test to_dict when first_seen_date is None."""
        result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            first_seen_date=None
        )
        
        data = result.to_dict()
        assert data["first_seen_date"] is None


class TestDomainHistory:
    """Test suite for DomainHistory model."""

    def test_create_basic_domain_history(self):
        """Test creating a basic DomainHistory."""
        history = DomainHistory(
            domain="example.com"
        )
        
        assert history.domain == "example.com"
        assert history.creation_date is None
        assert history.expiration_date is None
        assert history.registrar is None
        assert history.wayback_first_snapshot is None
        assert history.wayback_total_snapshots == 0
        assert history.ssl_first_seen is None
        assert history.age_days is None

    def test_create_full_domain_history(self):
        """Test creating a DomainHistory with all fields."""
        creation = datetime(2000, 1, 1)
        expiration = datetime(2025, 1, 1)
        wayback_first = datetime(2000, 2, 1)
        ssl_first = datetime(2005, 1, 1)
        
        history = DomainHistory(
            domain="example.com",
            creation_date=creation,
            expiration_date=expiration,
            registrar="Example Registrar Inc.",
            wayback_first_snapshot=wayback_first,
            wayback_total_snapshots=5000,
            ssl_first_seen=ssl_first,
            age_days=8000
        )
        
        assert history.creation_date == creation
        assert history.expiration_date == expiration
        assert history.registrar == "Example Registrar Inc."
        assert history.wayback_first_snapshot == wayback_first
        assert history.wayback_total_snapshots == 5000
        assert history.ssl_first_seen == ssl_first
        assert history.age_days == 8000

    def test_domain_history_to_dict(self):
        """Test converting DomainHistory to dictionary."""
        creation = datetime(2000, 1, 1)
        wayback_first = datetime(2000, 2, 1)
        
        history = DomainHistory(
            domain="example.com",
            creation_date=creation,
            registrar="Example Registrar Inc.",
            wayback_first_snapshot=wayback_first,
            wayback_total_snapshots=5000,
            age_days=8000
        )
        
        data = history.to_dict()
        
        assert isinstance(data, dict)
        assert data["domain"] == "example.com"
        assert data["creation_date"] == creation.isoformat()
        assert data["expiration_date"] is None
        assert data["registrar"] == "Example Registrar Inc."
        assert data["wayback_first_snapshot"] == wayback_first.isoformat()
        assert data["wayback_total_snapshots"] == 5000
        assert data["ssl_first_seen"] is None
        assert data["age_days"] == 8000


class TestLinkExtractionResult:
    """Test suite for LinkExtractionResult model."""

    def test_create_basic_link_extraction_result(self):
        """Test creating a basic LinkExtractionResult."""
        valid_link = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            reputation_score=85.0
        )
        
        result = LinkExtractionResult(
            extracted_links=["https://example.com", "https://invalid.com"],
            valid_links=[valid_link],
            invalid_links=["https://invalid.com"],
            total_links=2,
            valid_count=1,
            invalid_count=1,
            average_reputation_score=85.0
        )
        
        assert result.extracted_links == ["https://example.com", "https://invalid.com"]
        assert len(result.valid_links) == 1
        assert result.valid_links[0] == valid_link
        assert result.invalid_links == ["https://invalid.com"]
        assert result.total_links == 2
        assert result.valid_count == 1
        assert result.invalid_count == 1
        assert result.average_reputation_score == 85.0

    def test_link_extraction_result_to_dict(self):
        """Test converting LinkExtractionResult to dictionary."""
        valid_link = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            reputation_score=85.0
        )
        
        result = LinkExtractionResult(
            extracted_links=["https://example.com"],
            valid_links=[valid_link],
            invalid_links=[],
            total_links=1,
            valid_count=1,
            invalid_count=0,
            average_reputation_score=85.0
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["extracted_links"] == ["https://example.com"]
        assert len(data["valid_links"]) == 1
        assert isinstance(data["valid_links"][0], dict)
        assert data["valid_links"][0]["url"] == "https://example.com"
        assert data["invalid_links"] == []
        assert "summary" in data
        assert data["summary"]["total_links"] == 1
        assert data["summary"]["valid_count"] == 1
        assert data["summary"]["invalid_count"] == 0
        assert data["summary"]["average_reputation_score"] == 85.0
        assert "recommendation" in data["summary"]

    def test_get_recommendation_high_reputation(self):
        """Test recommendation for high reputation score."""
        result = LinkExtractionResult(
            extracted_links=[],
            valid_links=[],
            invalid_links=[],
            total_links=0,
            valid_count=0,
            invalid_count=0,
            average_reputation_score=85.0
        )
        
        recommendation = result._get_recommendation()
        assert "highly reputable" in recommendation

    def test_get_recommendation_moderate_reputation(self):
        """Test recommendation for moderate reputation score."""
        result = LinkExtractionResult(
            extracted_links=[],
            valid_links=[],
            invalid_links=[],
            total_links=0,
            valid_count=0,
            invalid_count=0,
            average_reputation_score=65.0
        )
        
        recommendation = result._get_recommendation()
        assert "moderate reputation" in recommendation

    def test_get_recommendation_low_reputation(self):
        """Test recommendation for low reputation score."""
        result = LinkExtractionResult(
            extracted_links=[],
            valid_links=[],
            invalid_links=[],
            total_links=0,
            valid_count=0,
            invalid_count=0,
            average_reputation_score=45.0
        )
        
        recommendation = result._get_recommendation()
        assert "low reputation" in recommendation

    def test_get_recommendation_suspicious(self):
        """Test recommendation for suspicious reputation score."""
        result = LinkExtractionResult(
            extracted_links=[],
            valid_links=[],
            invalid_links=[],
            total_links=0,
            valid_count=0,
            invalid_count=0,
            average_reputation_score=30.0
        )
        
        recommendation = result._get_recommendation()
        assert "suspicious" in recommendation