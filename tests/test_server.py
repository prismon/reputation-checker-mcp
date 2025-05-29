"""Unit tests for server.py"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from url_reputation_checker.models import (
    URLValidationResult, 
    DomainHistory, 
    LinkExtractionResult,
    ConfidenceLevel,
    ValidationLevel
)


class TestMCPServer:
    """Test suite for MCP server endpoints."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock CacheManager."""
        mock = AsyncMock()
        mock.get_validation_result = AsyncMock(return_value=None)
        mock.set_validation_result = AsyncMock()
        mock.get_domain_history = AsyncMock(return_value=None)
        mock.set_domain_history = AsyncMock()
        mock.get_stats = AsyncMock(return_value={
            "enabled": True,
            "validation_entries": 10,
            "history_entries": 5,
            "total_entries": 15
        })
        return mock

    @pytest.fixture
    def mock_validator(self):
        """Create a mock URLValidator."""
        mock = Mock()
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__ = AsyncMock(return_value=None)
        mock.check_url = AsyncMock()
        return mock

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock LinkExtractor."""
        mock = Mock()
        mock.extract_links = Mock()
        return mock

    @pytest.fixture
    def mock_history_checker(self):
        """Create a mock DomainHistoryChecker."""
        mock = AsyncMock()
        mock.get_domain_history = AsyncMock()
        mock.calculate_reputation_score = Mock()
        return mock

    @pytest.mark.asyncio
    async def test_check_links_reputation_success(self, mock_cache_manager, mock_validator, mock_history_checker):
        """Test successful check_links_reputation."""
        from url_reputation_checker.server import check_links_reputation
        
        # Setup mocks
        validation_result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            warnings=[],
            confidence_level=ConfidenceLevel.HIGH,
            reputation_score=0.0
        )
        mock_validator.check_url.return_value = validation_result
        
        domain_history = DomainHistory(
            domain="example.com",
            creation_date=datetime(2000, 1, 1),
            age_days=8000,
            wayback_first_snapshot=datetime(2000, 2, 1),
            wayback_total_snapshots=5000
        )
        mock_history_checker.get_domain_history.return_value = domain_history
        mock_history_checker.calculate_reputation_score.return_value = 85.0
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            with patch('url_reputation_checker.server.URLValidator', return_value=mock_validator):
                with patch('url_reputation_checker.server.history_checker', mock_history_checker):
                    results = await check_links_reputation(["https://example.com"])
        
        assert len(results) == 1
        result = results[0]
        assert result["url"] == "https://example.com"
        assert result["is_valid"] is True
        assert result["reputation_score"] == 85.0
        assert result["domain_age_days"] == 8000

    @pytest.mark.asyncio
    async def test_check_links_reputation_with_cache(self, mock_cache_manager):
        """Test check_links_reputation with cached results."""
        from url_reputation_checker.server import check_links_reputation
        
        cached_result = {
            "url": "https://cached.com",
            "is_valid": True,
            "status_code": 200,
            "reputation_score": 90.0
        }
        mock_cache_manager.get_validation_result.return_value = cached_result
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            results = await check_links_reputation(["https://cached.com"])
        
        assert len(results) == 1
        assert results[0] == cached_result

    @pytest.mark.asyncio
    async def test_check_links_reputation_empty_list(self):
        """Test check_links_reputation with empty URL list."""
        from url_reputation_checker.server import check_links_reputation
        
        results = await check_links_reputation([])
        assert results == []

    @pytest.mark.asyncio
    async def test_extract_and_check_links_success(self, mock_cache_manager, mock_validator, mock_extractor, mock_history_checker):
        """Test successful extract_and_check_links."""
        from url_reputation_checker.server import extract_and_check_links
        
        # Setup mocks
        mock_extractor.extract_links.return_value = ["https://example.com", "https://test.com"]
        
        validation_results = [
            URLValidationResult(
                url="https://example.com",
                is_valid=True,
                status_code=200,
                response_time=0.5,
                content_length=1000,
                ssl_valid=True,
                confidence_level=ConfidenceLevel.HIGH,
                reputation_score=0.0
            ),
            URLValidationResult(
                url="https://test.com",
                is_valid=False,
                status_code=404,
                response_time=0.5,
                content_length=0,
                ssl_valid=False,
                confidence_level=ConfidenceLevel.HIGH,
                reputation_score=0.0
            )
        ]
        mock_validator.check_url.side_effect = validation_results
        
        domain_history = DomainHistory(domain="example.com")
        mock_history_checker.get_domain_history.return_value = domain_history
        mock_history_checker.calculate_reputation_score.return_value = 75.0
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            with patch('url_reputation_checker.server.extractor', mock_extractor):
                with patch('url_reputation_checker.server.URLValidator', return_value=mock_validator):
                    with patch('url_reputation_checker.server.history_checker', mock_history_checker):
                        result = await extract_and_check_links("<a href='https://example.com'>Test</a>", "html")
        
        assert "extracted_links" in result
        assert "valid_links" in result
        assert "invalid_links" in result
        assert "summary" in result
        assert result["summary"]["total_links"] == 2
        assert result["summary"]["valid_count"] == 1
        assert result["summary"]["invalid_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_and_check_links_no_links(self, mock_extractor):
        """Test extract_and_check_links with no links found."""
        from url_reputation_checker.server import extract_and_check_links
        
        mock_extractor.extract_links.return_value = []
        
        with patch('url_reputation_checker.server.extractor', mock_extractor):
            result = await extract_and_check_links("No links here", "text")
        
        assert result["extracted_links"] == []
        assert result["summary"]["total_links"] == 0
        assert result["summary"]["recommendation"] == "No links found in content"

    @pytest.mark.asyncio
    async def test_validate_url_tool(self, mock_validator):
        """Test validate_url tool."""
        from url_reputation_checker.server import validate_url
        
        validation_result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            warnings=[],
            confidence_level=ConfidenceLevel.HIGH
        )
        mock_validator.check_url.return_value = validation_result
        
        with patch('url_reputation_checker.server.URLValidator', return_value=mock_validator):
            result = await validate_url("https://example.com")
        
        assert result["url"] == "https://example.com"
        assert result["is_valid"] is True
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_get_domain_history_tool(self, mock_cache_manager, mock_history_checker):
        """Test get_domain_history tool."""
        from url_reputation_checker.server import get_domain_history
        
        domain_history = DomainHistory(
            domain="example.com",
            creation_date=datetime(2000, 1, 1),
            registrar="Example Registrar Inc.",
            age_days=8000,
            wayback_first_snapshot=datetime(2000, 2, 1),
            wayback_total_snapshots=5000
        )
        mock_history_checker.get_domain_history.return_value = domain_history
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            with patch('url_reputation_checker.server.history_checker', mock_history_checker):
                result = await get_domain_history("example.com")
        
        assert result["domain"] == "example.com"
        assert result["age_days"] == 8000
        assert result["wayback_total_snapshots"] == 5000

    @pytest.mark.asyncio
    async def test_get_domain_history_cached(self, mock_cache_manager):
        """Test get_domain_history with cached result."""
        from url_reputation_checker.server import get_domain_history
        
        cached_history = {
            "domain": "cached.com",
            "age_days": 5000,
            "creation_date": "2010-01-01T00:00:00"
        }
        mock_cache_manager.get_domain_history.return_value = cached_history
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            result = await get_domain_history("cached.com")
        
        assert result == cached_history

    @pytest.mark.asyncio
    async def test_get_validation_report_empty(self):
        """Test validation report when no validations have been done."""
        from url_reputation_checker.server import get_validation_report
        
        with patch('url_reputation_checker.server.validation_history', []):
            report = await get_validation_report()
        
        assert report == "No URLs have been validated yet."

    @pytest.mark.asyncio
    async def test_get_validation_report_with_data(self):
        """Test validation report with validation history."""
        from url_reputation_checker.server import get_validation_report
        
        mock_history = [
            {
                "url": "https://example.com",
                "is_valid": True,
                "status_code": 200,
                "reputation_score": 85.0,
                "warnings": []
            },
            {
                "url": "https://invalid.com",
                "is_valid": False,
                "status_code": 404,
                "reputation_score": 10.0,
                "warnings": ["Not found"]
            }
        ]
        
        with patch('url_reputation_checker.server.validation_history', mock_history):
            report = await get_validation_report()
        
        assert "# URL Validation Report" in report
        assert "Total URLs validated: 2" in report
        assert "Valid URLs: 1" in report
        assert "Invalid URLs: 1" in report
        assert "✓ **https://example.com**" in report
        assert "✗ **https://invalid.com**" in report

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, mock_cache_manager):
        """Test get_cache_stats resource."""
        from url_reputation_checker.server import get_cache_stats
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            stats = await get_cache_stats()
        
        assert stats["enabled"] is True
        assert stats["total_entries"] == 15

    def test_server_initialization(self):
        """Test that server components are initialized."""
        from url_reputation_checker import server
        
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'cache_manager')
        assert hasattr(server, 'extractor')
        assert hasattr(server, 'history_checker')
        assert hasattr(server, 'validation_history')

    @pytest.mark.asyncio
    async def test_validation_history_tracking(self, mock_cache_manager, mock_validator, mock_history_checker):
        """Test that validation results are tracked in history."""
        from url_reputation_checker.server import check_links_reputation, validation_history
        
        # Clear history
        validation_history.clear()
        
        validation_result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            confidence_level=ConfidenceLevel.HIGH,
            reputation_score=0.0
        )
        mock_validator.check_url.return_value = validation_result
        
        domain_history = DomainHistory(domain="example.com")
        mock_history_checker.get_domain_history.return_value = domain_history
        mock_history_checker.calculate_reputation_score.return_value = 85.0
        
        with patch('url_reputation_checker.server.cache_manager', mock_cache_manager):
            with patch('url_reputation_checker.server.URLValidator', return_value=mock_validator):
                with patch('url_reputation_checker.server.history_checker', mock_history_checker):
                    await check_links_reputation(["https://example.com"])
        
        assert len(validation_history) == 1
        assert validation_history[0]["url"] == "https://example.com"