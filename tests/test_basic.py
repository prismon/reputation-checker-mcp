"""Basic tests for URL Reputation Checker that match actual implementation."""

import pytest
from url_reputation_checker.models import (
    ConfidenceLevel,
    ValidationLevel,
    URLValidationResult,
    DomainHistory,
    LinkExtractionResult
)
from datetime import datetime


class TestModels:
    """Test data models."""
    
    def test_confidence_level_enum(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
    
    def test_validation_level_enum(self):
        """Test ValidationLevel enum values."""
        assert ValidationLevel.BASIC.value == "basic"
        assert ValidationLevel.STANDARD.value == "standard"
        assert ValidationLevel.COMPREHENSIVE.value == "comprehensive"
    
    def test_url_validation_result_creation(self):
        """Test creating URLValidationResult."""
        result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            reputation_score=85.0,
            confidence_level=ConfidenceLevel.HIGH
        )
        
        assert result.url == "https://example.com"
        assert result.is_valid is True
        assert result.status_code == 200
        assert result.reputation_score == 85.0
        assert result.confidence_level == ConfidenceLevel.HIGH
    
    def test_url_validation_result_to_dict(self):
        """Test URLValidationResult to_dict method."""
        result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            reputation_score=85.0,
            confidence_level=ConfidenceLevel.HIGH,
            warnings=["Test warning"]
        )
        
        data = result.to_dict()
        assert data["url"] == "https://example.com"
        assert data["is_valid"] is True
        assert data["reputation_score"] == 85.0
        assert data["confidence_level"] == "high"
        assert data["warnings"] == ["Test warning"]
    
    def test_domain_history_creation(self):
        """Test creating DomainHistory."""
        history = DomainHistory(
            domain="example.com",
            creation_date=datetime(2000, 1, 1),
            registrar="Test Registrar",
            age_days=8000,
            wayback_total_snapshots=5000
        )
        
        assert history.domain == "example.com"
        assert history.creation_date == datetime(2000, 1, 1)
        assert history.registrar == "Test Registrar"
        assert history.age_days == 8000
        assert history.wayback_total_snapshots == 5000
    
    def test_link_extraction_result_creation(self):
        """Test creating LinkExtractionResult."""
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
            extracted_links=["https://example.com", "https://test.com"],
            valid_links=[valid_link],
            invalid_links=["https://invalid.com"],
            total_links=3,
            valid_count=1,
            invalid_count=1,
            average_reputation_score=85.0
        )
        
        assert result.total_links == 3
        assert result.valid_count == 1
        assert result.invalid_count == 1
        assert result.average_reputation_score == 85.0
        assert len(result.valid_links) == 1
        assert len(result.invalid_links) == 1
    
    def test_link_extraction_result_recommendation(self):
        """Test recommendation generation."""
        valid_link = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            reputation_score=85.0
        )
        
        # High reputation
        result = LinkExtractionResult(
            extracted_links=["https://example.com"],
            valid_links=[valid_link],
            invalid_links=[],
            total_links=1,
            valid_count=1,
            invalid_count=0,
            average_reputation_score=85.0
        )
        assert "highly reputable" in result._get_recommendation()
        
        # Low reputation
        result.average_reputation_score = 30.0
        assert "suspicious" in result._get_recommendation()