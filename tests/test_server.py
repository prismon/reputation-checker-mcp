"""Tests for the main server module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from url_reputation_checker.models import (
    URLValidationResult,
    DomainHistory,
    ConfidenceLevel
)


class TestMCPServer:
    """Test MCP server tools and resources."""
    
    @pytest.mark.asyncio
    async def test_check_url_reputation_success(self):
        """Test successful URL reputation check."""
        from url_reputation_checker.server import check_url_reputation
        
        # Mock the dependencies
        mock_validation_result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=100,
            content_length=1000,
            warnings=[],
            confidence_level=ConfidenceLevel.HIGH,
            ssl_valid=True
        )
        
        mock_domain_history = DomainHistory(
            domain="example.com",
            creation_date=datetime(2000, 1, 1),
            age_days=8000,
            wayback_first_snapshot=datetime(2001, 1, 1),
            wayback_total_snapshots=1000
        )
        
        with patch('url_reputation_checker.server.cache_manager') as mock_cache:
            mock_cache.get_validation_result = AsyncMock(return_value=None)
            mock_cache.set_validation_result = AsyncMock()
            
            with patch('url_reputation_checker.server.URLValidator') as mock_validator_class:
                mock_validator = AsyncMock()
                mock_validator_class.return_value.__aenter__.return_value = mock_validator
                mock_validator.check_url = AsyncMock(return_value=mock_validation_result)
                
                with patch('url_reputation_checker.server.history_checker') as mock_history:
                    mock_history.get_domain_history = AsyncMock(return_value=mock_domain_history)
                    mock_history.calculate_reputation_score = Mock(return_value=85.0)
                    
                    result = await check_url_reputation("https://example.com")
                    
                    assert result['url'] == "https://example.com"
                    assert result['is_valid'] is True
                    assert result['reputation_score'] == 85.0
                    assert result['domain_age_days'] == 8000
    
    @pytest.mark.asyncio
    async def test_check_url_reputation_with_cache(self):
        """Test URL reputation check returns cached result."""
        from url_reputation_checker.server import check_url_reputation
        
        cached_result = {
            'url': 'https://cached.com',
            'is_valid': True,
            'reputation_score': 90.0,
            'status_code': 200
        }
        
        with patch('url_reputation_checker.server.cache_manager') as mock_cache:
            mock_cache.get_validation_result = AsyncMock(return_value=cached_result)
            
            result = await check_url_reputation("https://cached.com")
            
            assert result == cached_result
            mock_cache.get_validation_result.assert_called_once_with("https://cached.com")
    
    @pytest.mark.asyncio
    async def test_check_url_reputation_error(self):
        """Test URL reputation check handles errors gracefully."""
        from url_reputation_checker.server import check_url_reputation
        
        with patch('url_reputation_checker.server.cache_manager') as mock_cache:
            mock_cache.get_validation_result = AsyncMock(side_effect=Exception("Test error"))
            
            result = await check_url_reputation("https://error.com")
            
            assert result['url'] == "https://error.com"
            assert result['is_valid'] is False
            assert result['reputation_score'] == 0
            assert 'error' in result
            assert "Failed to check URL" in result['error']
    
    def test_server_initialization(self):
        """Test that server components are initialized."""
        from url_reputation_checker import server
        
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'cache_manager')
        assert hasattr(server, 'history_checker')