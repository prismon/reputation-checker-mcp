"""Unit tests for cache.py"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
from redis.asyncio import Redis

from url_reputation_checker.cache import CacheManager


class TestCacheManager:
    """Test suite for CacheManager."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock(spec=Redis)
        mock.ping = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.keys = AsyncMock(return_value=[])
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    async def cache_manager(self):
        """Create a CacheManager instance."""
        manager = CacheManager()
        yield manager
        if manager.redis:
            await manager.disconnect()

    @pytest.mark.asyncio
    async def test_init(self):
        """Test CacheManager initialization."""
        manager = CacheManager()
        assert manager.redis_url == "redis://localhost:6379"
        assert manager.redis is None
        assert manager.ttl_valid == 86400
        assert manager.ttl_invalid == 3600
        assert manager.ttl_history == 604800

    @pytest.mark.asyncio
    async def test_init_with_custom_url(self):
        """Test CacheManager initialization with custom Redis URL."""
        manager = CacheManager(redis_url="redis://custom:6380")
        assert manager.redis_url == "redis://custom:6380"

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis):
        """Test successful Redis connection."""
        with patch('url_reputation_checker.cache.Redis.from_url', return_value=mock_redis):
            manager = CacheManager()
            await manager.connect()
            
            assert manager.redis is not None
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test Redis connection failure."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('url_reputation_checker.cache.Redis.from_url', return_value=mock_redis):
            manager = CacheManager()
            await manager.connect()
            
            assert manager.redis is None

    @pytest.mark.asyncio
    async def test_ensure_connected(self, mock_redis):
        """Test _ensure_connected method."""
        with patch('url_reputation_checker.cache.Redis.from_url', return_value=mock_redis):
            manager = CacheManager()
            assert manager.redis is None
            
            await manager._ensure_connected()
            assert manager.redis is not None

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis):
        """Test disconnecting from Redis."""
        manager = CacheManager()
        manager.redis = mock_redis
        
        await manager.disconnect()
        mock_redis.close.assert_called_once()

    def test_get_cache_key_short(self, cache_manager):
        """Test cache key generation for short identifiers."""
        key = cache_manager._get_cache_key("validation", "https://example.com")
        assert key == "url_reputation:validation:https://example.com"

    def test_get_cache_key_long(self, cache_manager):
        """Test cache key generation for long identifiers."""
        long_url = "https://example.com/" + "a" * 200
        key = cache_manager._get_cache_key("validation", long_url)
        
        assert key.startswith("url_reputation:validation:")
        # Should use MD5 hash for long URLs
        assert len(key) < len("url_reputation:validation:" + long_url)

    @pytest.mark.asyncio
    async def test_get_validation_result_cache_hit(self, cache_manager, mock_redis):
        """Test getting cached validation result."""
        cached_data = {
            "url": "https://example.com",
            "is_valid": True,
            "status_code": 200
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()
        cache_manager.redis = mock_redis
        
        result = await cache_manager.get_validation_result("https://example.com")
        
        assert result == cached_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_validation_result_cache_miss(self, cache_manager, mock_redis):
        """Test cache miss for validation result."""
        mock_redis.get.return_value = None
        cache_manager.redis = mock_redis
        
        result = await cache_manager.get_validation_result("https://example.com")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_validation_result_no_redis(self, cache_manager):
        """Test getting validation result when Redis is not available."""
        cache_manager.redis = None
        
        result = await cache_manager.get_validation_result("https://example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_validation_result_valid(self, cache_manager, mock_redis):
        """Test caching a valid URL validation result."""
        cache_manager.redis = mock_redis
        
        result = {
            "url": "https://example.com",
            "is_valid": True,
            "status_code": 200
        }
        
        await cache_manager.set_validation_result("https://example.com", result, is_valid=True)
        
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "url_reputation:validation:https://example.com"
        assert args[1] == 86400  # ttl_valid
        
        # Check that timestamp was added
        data = json.loads(args[2])
        assert 'cached_at' in data

    @pytest.mark.asyncio
    async def test_set_validation_result_invalid(self, cache_manager, mock_redis):
        """Test caching an invalid URL validation result."""
        cache_manager.redis = mock_redis
        
        result = {
            "url": "https://invalid.com",
            "is_valid": False
        }
        
        await cache_manager.set_validation_result("https://invalid.com", result, is_valid=False)
        
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[1] == 3600  # ttl_invalid

    @pytest.mark.asyncio
    async def test_set_validation_result_no_redis(self, cache_manager):
        """Test setting validation result when Redis is not available."""
        cache_manager.redis = None
        
        # Should not raise exception
        await cache_manager.set_validation_result("https://example.com", {}, True)

    @pytest.mark.asyncio
    async def test_get_domain_history_cache_hit(self, cache_manager, mock_redis):
        """Test getting cached domain history."""
        cached_data = {
            "domain": "example.com",
            "creation_date": "2000-01-01",
            "age_days": 8000
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()
        cache_manager.redis = mock_redis
        
        result = await cache_manager.get_domain_history("example.com")
        
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_set_domain_history(self, cache_manager, mock_redis):
        """Test caching domain history."""
        cache_manager.redis = mock_redis
        
        history = {
            "domain": "example.com",
            "creation_date": "2000-01-01",
            "age_days": 8000
        }
        
        await cache_manager.set_domain_history("example.com", history)
        
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "url_reputation:history:example.com"
        assert args[1] == 604800  # ttl_history

    @pytest.mark.asyncio
    async def test_get_stats_with_redis(self, cache_manager, mock_redis):
        """Test getting cache statistics."""
        mock_redis.keys.side_effect = [
            [b"url_reputation:validation:1", b"url_reputation:validation:2"],
            [b"url_reputation:history:1"]
        ]
        cache_manager.redis = mock_redis
        
        stats = await cache_manager.get_stats()
        
        assert stats["enabled"] is True
        assert stats["validation_entries"] == 2
        assert stats["history_entries"] == 1
        assert stats["total_entries"] == 3

    @pytest.mark.asyncio
    async def test_get_stats_no_redis(self, cache_manager):
        """Test getting stats when Redis is not available."""
        cache_manager.redis = None
        
        stats = await cache_manager.get_stats()
        
        assert stats["enabled"] is False

    @pytest.mark.asyncio
    async def test_get_stats_ensures_connection(self, mock_redis):
        """Test that get_stats ensures connection."""
        with patch('url_reputation_checker.cache.Redis.from_url', return_value=mock_redis):
            manager = CacheManager()
            mock_redis.keys.return_value = []
            
            stats = await manager.get_stats()
            
            # Should have connected
            assert manager.redis is not None
            assert stats["enabled"] is True

    @pytest.mark.asyncio
    async def test_clear_cache(self, cache_manager, mock_redis):
        """Test clearing the cache."""
        mock_redis.keys.return_value = [
            b"url_reputation:validation:1",
            b"url_reputation:validation:2",
            b"url_reputation:history:1"
        ]
        cache_manager.redis = mock_redis
        
        await cache_manager.clear_cache()
        
        mock_redis.keys.assert_called_with("url_reputation:*")
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_no_keys(self, cache_manager, mock_redis):
        """Test clearing cache when no keys exist."""
        mock_redis.keys.return_value = []
        cache_manager.redis = mock_redis
        
        await cache_manager.clear_cache()
        
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_handling(self, cache_manager, mock_redis):
        """Test that exceptions are handled gracefully."""
        # Make all Redis operations raise exceptions
        mock_redis.get.side_effect = Exception("Redis error")
        mock_redis.setex.side_effect = Exception("Redis error")
        mock_redis.keys.side_effect = Exception("Redis error")
        cache_manager.redis = mock_redis
        
        # All operations should return None/empty without raising
        result = await cache_manager.get_validation_result("https://example.com")
        assert result is None
        
        await cache_manager.set_validation_result("https://example.com", {}, True)
        
        stats = await cache_manager.get_stats()
        assert stats["enabled"] is False