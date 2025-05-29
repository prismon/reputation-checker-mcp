"""Unit tests for validators.py"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
import time
from datetime import datetime

from url_reputation_checker.validators import URLValidator
from url_reputation_checker.models import (
    URLValidationResult, 
    ConfidenceLevel, 
    ValidationLevel
)


class TestURLValidator:
    """Test suite for URLValidator."""

    @pytest.fixture
    def validator(self):
        """Create a URLValidator instance."""
        return URLValidator(timeout=10.0, user_agent="Test-Agent/1.0")

    @pytest.fixture
    def mock_httpx_response(self):
        """Create a mock httpx response."""
        response = Mock()
        response.status_code = 200
        response.content = b"Test content"
        response.text = "Test content"
        response.headers = {"content-type": "text/html"}
        response.url = "https://example.com"
        response.history = []
        return response

    def test_init(self):
        """Test URLValidator initialization."""
        validator = URLValidator()
        assert validator.timeout == 10.0
        assert validator.user_agent == "URL-Reputation-Checker/1.0"
        assert validator.client is None

    def test_init_custom_params(self):
        """Test URLValidator initialization with custom parameters."""
        validator = URLValidator(timeout=5.0, user_agent="Custom-Agent")
        assert validator.timeout == 5.0
        assert validator.user_agent == "Custom-Agent"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with URLValidator() as validator:
            assert validator.client is not None
            assert isinstance(validator.client, httpx.AsyncClient)
        # Client should be closed after exiting context

    def test_is_valid_url(self, validator):
        """Test URL format validation."""
        assert validator.is_valid_url("https://example.com") is True
        assert validator.is_valid_url("http://test.com/path") is True
        assert validator.is_valid_url("not-a-url") is False
        assert validator.is_valid_url("") is False
        assert validator.is_valid_url("ftp://example.com") is True

    @pytest.mark.asyncio
    async def test_check_url_invalid_format(self, validator):
        """Test check_url with invalid URL format."""
        async with validator:
            result = await validator.check_url("not-a-valid-url")
        
        assert isinstance(result, URLValidationResult)
        assert result.is_valid is False
        assert result.status_code == 0
        assert "Invalid URL format" in result.warnings
        assert result.confidence_level == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_check_url_basic_valid(self, validator, mock_httpx_response):
        """Test basic validation of a valid URL."""
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        result = await validator.check_url("https://example.com", ValidationLevel.BASIC)
        
        assert result.is_valid is True
        assert result.status_code == 200
        assert result.content_length == len(b"Test content")
        assert result.ssl_valid is True  # HTTPS URL
        assert result.metadata["final_url"] == "https://example.com"
        assert result.metadata["redirect_count"] == 0

    @pytest.mark.asyncio
    async def test_check_url_http(self, validator, mock_httpx_response):
        """Test validation of HTTP (non-HTTPS) URL."""
        mock_client = AsyncMock()
        mock_httpx_response.url = "http://example.com"
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        result = await validator.check_url("http://example.com", ValidationLevel.BASIC)
        
        assert result.ssl_valid is False

    @pytest.mark.asyncio
    async def test_check_url_timeout(self, validator):
        """Test URL validation with timeout."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        
        validator.client = mock_client
        result = await validator.check_url("https://example.com")
        
        assert result.is_valid is False
        assert result.status_code == 0
        assert result.response_time == validator.timeout
        assert "Request timeout" in result.warnings
        assert result.confidence_level == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_check_url_exception(self, validator):
        """Test URL validation with general exception."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        
        validator.client = mock_client
        result = await validator.check_url("https://example.com")
        
        assert result.is_valid is False
        assert "Request failed: Network error" in result.warnings

    @pytest.mark.asyncio
    async def test_check_url_redirect(self, validator, mock_httpx_response):
        """Test URL validation with redirects."""
        mock_client = AsyncMock()
        mock_httpx_response.history = [Mock(), Mock()]  # Two redirects
        mock_httpx_response.url = "https://www.example.com"
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        result = await validator.check_url("https://example.com")
        
        assert result.metadata["final_url"] == "https://www.example.com"
        assert result.metadata["redirect_count"] == 2

    @pytest.mark.asyncio
    async def test_check_url_standard_level(self, validator, mock_httpx_response):
        """Test standard level validation."""
        mock_client = AsyncMock()
        mock_httpx_response.text = "<html><body>Valid content with sufficient length for testing</body></html>"
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        validator._validate_ssl = AsyncMock(return_value=True)
        
        result = await validator.check_url("https://example.com", ValidationLevel.STANDARD)
        
        assert result.is_valid is True
        # Should have performed content validation
        assert len(result.warnings) == 0  # No warnings for valid content

    @pytest.mark.asyncio
    async def test_check_url_comprehensive_level(self, validator, mock_httpx_response):
        """Test comprehensive level validation."""
        mock_client = AsyncMock()
        mock_httpx_response.url = "https://example.com/blog/2024/03/15/ai-research-paper"
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        result = await validator.check_url(mock_httpx_response.url, ValidationLevel.COMPREHENSIVE)
        
        # Should check for suspicious patterns
        assert any("AI hallucinations" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_ssl_valid(self, validator):
        """Test SSL validation for valid certificate."""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = Mock()
            mock_writer = Mock()
            mock_writer.wait_closed = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            
            result = await validator._validate_ssl("https://example.com")
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_ssl_invalid(self, validator):
        """Test SSL validation for invalid certificate."""
        with patch('asyncio.open_connection', side_effect=Exception("SSL error")):
            result = await validator._validate_ssl("https://example.com")
            assert result is False

    def test_validate_content_short(self, validator):
        """Test content validation for short content."""
        warnings = validator._validate_content("Short", {"content-type": "text/html"})
        assert any("Very short content" in w for w in warnings)

    def test_validate_content_parking_page(self, validator):
        """Test content validation for parking page."""
        content = "<html><body><h1>This domain is for sale!</h1></body></html>"
        warnings = validator._validate_content(content, {"content-type": "text/html"})
        assert any("parking page" in w for w in warnings)

    def test_validate_content_invalid_html(self, validator):
        """Test content validation for invalid HTML."""
        content = "<div>No html or body tags</div>"
        warnings = validator._validate_content(content, {"content-type": "text/html"})
        assert any("Invalid HTML structure" in w for w in warnings)

    def test_validate_content_valid(self, validator):
        """Test content validation for valid content."""
        content = "<html><body><h1>Welcome</h1><p>This is a valid website with real content.</p></body></html>"
        warnings = validator._validate_content(content, {"content-type": "text/html"})
        assert len(warnings) == 0

    def test_check_suspicious_patterns_ai_hallucination(self, validator):
        """Test detection of AI hallucination patterns."""
        warnings = validator._check_suspicious_patterns(
            "https://example.com/blog/2024/03/15/groundbreaking-ai-research",
            ""
        )
        assert any("AI hallucinations" in w for w in warnings)

    def test_check_suspicious_patterns_deep_path(self, validator):
        """Test detection of deep URL paths."""
        warnings = validator._check_suspicious_patterns(
            "https://example.com/a/b/c/d/e/f/g/h",
            ""
        )
        assert any("deep URL path" in w for w in warnings)

    def test_check_suspicious_patterns_excessive_subdomains(self, validator):
        """Test detection of excessive subdomains."""
        warnings = validator._check_suspicious_patterns(
            "https://a.b.c.d.example.com",
            ""
        )
        assert any("Excessive subdomains" in w for w in warnings)

    def test_check_suspicious_patterns_typosquatting(self, validator):
        """Test detection of typosquatting."""
        warnings = validator._check_suspicious_patterns(
            "https://gihub.com",  # Missing 't' in github
            ""
        )
        assert any("typosquatting" in w for w in warnings)

    def test_is_typosquatting_similar(self, validator):
        """Test typosquatting detection for similar domains."""
        assert validator._is_typosquatting("gihub.com", "github.com") is True
        assert validator._is_typosquatting("gogle.com", "google.com") is True
        assert validator._is_typosquatting("amazom.com", "amazon.com") is True

    def test_is_typosquatting_identical(self, validator):
        """Test typosquatting detection for identical domains."""
        assert validator._is_typosquatting("github.com", "github.com") is False

    def test_is_typosquatting_different(self, validator):
        """Test typosquatting detection for different domains."""
        assert validator._is_typosquatting("example.com", "github.com") is False

    def test_levenshtein_distance(self, validator):
        """Test Levenshtein distance calculation."""
        assert validator._levenshtein_distance("kitten", "sitting") == 3
        assert validator._levenshtein_distance("saturday", "sunday") == 3
        assert validator._levenshtein_distance("", "abc") == 3
        assert validator._levenshtein_distance("abc", "abc") == 0

    def test_determine_confidence_invalid(self, validator):
        """Test confidence determination for invalid URLs."""
        confidence = validator._determine_confidence(is_valid=False, warnings=[])
        assert confidence == ConfidenceLevel.HIGH

    def test_determine_confidence_no_warnings(self, validator):
        """Test confidence determination with no warnings."""
        confidence = validator._determine_confidence(is_valid=True, warnings=[])
        assert confidence == ConfidenceLevel.HIGH

    def test_determine_confidence_few_warnings(self, validator):
        """Test confidence determination with few warnings."""
        confidence = validator._determine_confidence(is_valid=True, warnings=["Warning 1", "Warning 2"])
        assert confidence == ConfidenceLevel.MEDIUM

    def test_determine_confidence_many_warnings(self, validator):
        """Test confidence determination with many warnings."""
        confidence = validator._determine_confidence(
            is_valid=True, 
            warnings=["Warning 1", "Warning 2", "Warning 3", "Warning 4"]
        )
        assert confidence == ConfidenceLevel.LOW

    @pytest.mark.asyncio
    async def test_check_url_non_200_valid_status(self, validator, mock_httpx_response):
        """Test validation with non-200 but valid status codes."""
        mock_client = AsyncMock()
        mock_httpx_response.status_code = 301  # Redirect
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        result = await validator.check_url("https://example.com")
        
        assert result.is_valid is True
        assert result.status_code == 301

    @pytest.mark.asyncio
    async def test_check_url_invalid_status(self, validator, mock_httpx_response):
        """Test validation with invalid status codes."""
        mock_client = AsyncMock()
        mock_httpx_response.status_code = 404
        mock_client.get.return_value = mock_httpx_response
        
        validator.client = mock_client
        result = await validator.check_url("https://example.com")
        
        assert result.is_valid is False
        assert result.status_code == 404