"""Unit tests for history.py"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import whois
import waybackpy

from url_reputation_checker.history import DomainHistoryChecker
from url_reputation_checker.models import DomainHistory, URLValidationResult, ConfidenceLevel


class TestDomainHistoryChecker:
    """Test suite for DomainHistoryChecker."""

    @pytest.fixture
    def checker(self):
        """Create a DomainHistoryChecker instance."""
        return DomainHistoryChecker(user_agent="Test-Agent/1.0")

    @pytest.fixture
    def mock_validation_result(self):
        """Create a mock URLValidationResult."""
        return URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            warnings=[],
            confidence_level=ConfidenceLevel.HIGH
        )

    def test_init(self):
        """Test DomainHistoryChecker initialization."""
        checker = DomainHistoryChecker()
        assert checker.user_agent == "URL-Reputation-Checker/1.0"

    def test_init_custom_user_agent(self):
        """Test DomainHistoryChecker with custom user agent."""
        checker = DomainHistoryChecker(user_agent="Custom-Agent")
        assert checker.user_agent == "Custom-Agent"

    @pytest.mark.asyncio
    async def test_get_domain_history_success(self, checker):
        """Test successful domain history retrieval."""
        creation_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
        expiration_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        
        mock_whois_info = {
            'creation_date': creation_date,
            'expiration_date': expiration_date,
            'registrar': 'Example Registrar Inc.'
        }
        
        mock_wayback_info = {
            'first_snapshot': datetime(2000, 2, 1, tzinfo=timezone.utc),
            'total_snapshots': 5000
        }
        
        with patch.object(checker, '_get_whois_info', return_value=mock_whois_info):
            with patch.object(checker, '_get_wayback_info', return_value=mock_wayback_info):
                history = await checker.get_domain_history("https://example.com")
        
        assert isinstance(history, DomainHistory)
        assert history.domain == "example.com"
        assert history.creation_date == creation_date
        assert history.expiration_date == expiration_date
        assert history.registrar == "Example Registrar Inc."
        assert history.wayback_first_snapshot == datetime(2000, 2, 1, tzinfo=timezone.utc)
        assert history.wayback_total_snapshots == 5000
        assert history.age_days is not None
        assert history.age_days > 8000  # More than 8000 days old

    @pytest.mark.asyncio
    async def test_get_domain_history_subdomain(self, checker):
        """Test domain history extraction from subdomain URL."""
        with patch.object(checker, '_get_whois_info', return_value={}):
            with patch.object(checker, '_get_wayback_info', return_value={}):
                history = await checker.get_domain_history("https://subdomain.example.com/path")
        
        assert history.domain == "example.com"

    @pytest.mark.asyncio
    async def test_get_domain_history_with_exceptions(self, checker):
        """Test domain history when some checks fail."""
        with patch.object(checker, '_get_whois_info', side_effect=Exception("WHOIS failed")):
            with patch.object(checker, '_get_wayback_info', return_value={'total_snapshots': 100}):
                history = await checker.get_domain_history("https://example.com")
        
        assert history.domain == "example.com"
        assert history.creation_date is None
        assert history.registrar is None
        assert history.wayback_total_snapshots == 100

    @pytest.mark.asyncio
    async def test_get_whois_info_success(self, checker):
        """Test successful WHOIS lookup."""
        mock_whois_data = Mock()
        mock_whois_data.creation_date = datetime(2000, 1, 1)
        mock_whois_data.expiration_date = datetime(2025, 1, 1)
        mock_whois_data.registrar = 'Test Registrar'
        
        with patch('whois.whois', return_value=mock_whois_data):
            info = await checker._get_whois_info("example.com")
        
        assert 'creation_date' in info
        assert 'expiration_date' in info
        assert info['registrar'] == 'Test Registrar'

    @pytest.mark.asyncio
    async def test_get_whois_info_list_dates(self, checker):
        """Test WHOIS with list of dates."""
        mock_whois_data = Mock()
        mock_whois_data.creation_date = [datetime(2000, 1, 1), datetime(2000, 1, 2)]
        mock_whois_data.expiration_date = [datetime(2025, 1, 1)]
        mock_whois_data.registrar = 'Test Registrar'
        
        with patch('whois.whois', return_value=mock_whois_data):
            info = await checker._get_whois_info("example.com")
        
        # Should use first date from list
        assert info['creation_date'].day == 1

    @pytest.mark.asyncio
    async def test_get_whois_info_exception(self, checker):
        """Test WHOIS lookup failure."""
        with patch('whois.whois', side_effect=Exception("Lookup failed")):
            info = await checker._get_whois_info("example.com")
        
        assert info == {}

    @pytest.mark.asyncio
    async def test_get_wayback_info_success(self, checker):
        """Test successful Wayback Machine lookup."""
        mock_oldest = Mock()
        mock_oldest.timestamp = "20000201120000"  # Feb 1, 2000
        
        mock_cdx = [1, 2, 3, 4, 5]  # 5 snapshots
        
        mock_wb = Mock()
        mock_wb.oldest.return_value = mock_oldest
        mock_wb.cdx_api.return_value = mock_cdx
        
        with patch('waybackpy.Url', return_value=mock_wb):
            info = await checker._get_wayback_info("https://example.com")
        
        assert info['first_snapshot'] == datetime(2000, 2, 1, tzinfo=timezone.utc)
        assert info['total_snapshots'] == 5

    @pytest.mark.asyncio
    async def test_get_wayback_info_no_snapshots(self, checker):
        """Test Wayback Machine with no snapshots."""
        mock_wb = Mock()
        mock_wb.oldest.side_effect = Exception("No archives")
        mock_wb.cdx_api.return_value = []
        
        with patch('waybackpy.Url', return_value=mock_wb):
            info = await checker._get_wayback_info("https://example.com")
        
        assert info['first_snapshot'] is None
        assert info['total_snapshots'] == 0

    @pytest.mark.asyncio
    async def test_get_wayback_info_exception(self, checker):
        """Test Wayback Machine lookup failure."""
        with patch('waybackpy.Url', side_effect=Exception("API error")):
            info = await checker._get_wayback_info("https://example.com")
        
        assert info == {}

    def test_ensure_timezone_with_tz(self, checker):
        """Test _ensure_timezone with timezone-aware datetime."""
        dt = datetime(2000, 1, 1, tzinfo=timezone.utc)
        result = checker._ensure_timezone(dt)
        assert result == dt
        assert result.tzinfo is not None

    def test_ensure_timezone_without_tz(self, checker):
        """Test _ensure_timezone with naive datetime."""
        dt = datetime(2000, 1, 1)
        result = checker._ensure_timezone(dt)
        assert result.tzinfo == timezone.utc

    def test_ensure_timezone_none(self, checker):
        """Test _ensure_timezone with None."""
        result = checker._ensure_timezone(None)
        assert result is None

    def test_calculate_reputation_score_excellent(self, checker, mock_validation_result):
        """Test reputation calculation for excellent domain."""
        history = DomainHistory(
            domain="example.com",
            creation_date=datetime(2000, 1, 1, tzinfo=timezone.utc),
            age_days=365 * 20,  # 20 years
            wayback_total_snapshots=500
        )
        
        score = checker.calculate_reputation_score(history, mock_validation_result)
        
        # Should get maximum points in all categories
        assert score >= 90

    def test_calculate_reputation_score_new_domain(self, checker, mock_validation_result):
        """Test reputation calculation for new domain."""
        history = DomainHistory(
            domain="newsite.com",
            creation_date=datetime.now(timezone.utc) - timedelta(days=30),
            age_days=30,
            wayback_total_snapshots=0
        )
        
        score = checker.calculate_reputation_score(history, mock_validation_result)
        
        # New domain should score low
        assert score < 50

    def test_calculate_reputation_score_domain_age_scoring(self, checker, mock_validation_result):
        """Test domain age scoring categories."""
        # Test each age bracket
        test_cases = [
            (365 * 6, 30),   # 6 years -> 30 points
            (365 * 3, 20),   # 3 years -> 20 points
            (365 * 1.5, 15), # 1.5 years -> 15 points
            (200, 10),       # 200 days -> 10 points
            (100, 5),        # 100 days -> 5 points
            (30, 2),         # 30 days -> 2 points
        ]
        
        for age_days, expected_min in test_cases:
            history = DomainHistory(domain="test.com", age_days=age_days)
            score = checker.calculate_reputation_score(history, mock_validation_result)
            assert score >= expected_min

    def test_calculate_reputation_score_wayback_scoring(self, checker, mock_validation_result):
        """Test Wayback Machine scoring categories."""
        test_cases = [
            (150, 20),  # 150 snapshots -> 20 points
            (75, 15),   # 75 snapshots -> 15 points
            (30, 10),   # 30 snapshots -> 10 points
            (10, 5),    # 10 snapshots -> 5 points
            (3, 2),     # 3 snapshots -> 2 points
        ]
        
        for snapshots, expected_min in test_cases:
            history = DomainHistory(domain="test.com", wayback_total_snapshots=snapshots)
            score = checker.calculate_reputation_score(history, mock_validation_result)
            assert score >= expected_min

    def test_calculate_reputation_score_technical_factors(self, checker):
        """Test technical factors scoring."""
        history = DomainHistory(domain="test.com")
        
        # Test with good technical factors
        good_result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.5,
            content_length=1000,
            ssl_valid=True,
            warnings=[]
        )
        score_good = checker.calculate_reputation_score(history, good_result)
        
        # Test with poor technical factors
        poor_result = URLValidationResult(
            url="http://example.com",
            is_valid=True,
            status_code=404,
            response_time=3.0,
            content_length=100,
            ssl_valid=False,
            warnings=[]
        )
        score_poor = checker.calculate_reputation_score(history, poor_result)
        
        assert score_good > score_poor

    def test_calculate_reputation_score_warnings_impact(self, checker):
        """Test impact of warnings on reputation score."""
        history = DomainHistory(domain="test.com", age_days=365)
        
        # Test with different warning counts
        test_cases = [
            ([], 25),      # No warnings -> 25 consistency points
            (["w1"], 15),  # 1 warning -> 15 points
            (["w1", "w2"], 10),  # 2 warnings -> 10 points
            (["w1", "w2", "w3"], 5),  # 3 warnings -> 5 points
            (["w1", "w2", "w3", "w4"], 0),  # 4+ warnings -> 0 points
        ]
        
        for warnings, expected_consistency in test_cases:
            result = URLValidationResult(
                url="https://example.com",
                is_valid=True,
                status_code=200,
                response_time=1.0,
                content_length=1000,
                ssl_valid=True,
                warnings=warnings
            )
            score = checker.calculate_reputation_score(history, result)
            # Check that consistency score is as expected
            # (Score includes other factors, so we can't check exact value)
            assert score >= expected_consistency

    def test_calculate_reputation_score_max_100(self, checker):
        """Test that reputation score is capped at 100."""
        # Create perfect conditions
        history = DomainHistory(
            domain="example.com",
            age_days=365 * 10,  # 10 years
            wayback_total_snapshots=1000
        )
        
        perfect_result = URLValidationResult(
            url="https://example.com",
            is_valid=True,
            status_code=200,
            response_time=0.1,
            content_length=10000,
            ssl_valid=True,
            warnings=[]
        )
        
        score = checker.calculate_reputation_score(history, perfect_result)
        assert score == 100.0

    @pytest.mark.asyncio
    async def test_get_domain_history_no_age_days(self, checker):
        """Test domain history when creation date is missing."""
        mock_whois_info = {
            'registrar': 'Example Registrar'
        }
        
        with patch.object(checker, '_get_whois_info', return_value=mock_whois_info):
            with patch.object(checker, '_get_wayback_info', return_value={}):
                history = await checker.get_domain_history("https://example.com")
        
        assert history.age_days is None