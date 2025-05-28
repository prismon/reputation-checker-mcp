"""Caching utilities for URL reputation checker."""

import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

import aioredis
from aioredis import Redis


class CacheManager:
    """Manage caching for URL validation results."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[Redis] = None
        self.ttl_valid = 86400  # 24 hours for valid URLs
        self.ttl_invalid = 3600  # 1 hour for invalid URLs
        self.ttl_history = 604800  # 7 days for domain history
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
        except Exception:
            # If Redis is not available, caching will be disabled
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key."""
        # Use hash for long URLs
        if len(identifier) > 200:
            identifier = hashlib.md5(identifier.encode()).hexdigest()
        return f"url_reputation:{prefix}:{identifier}"
    
    async def get_validation_result(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        if not self.redis:
            return None
        
        try:
            key = self._get_cache_key("validation", url)
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        
        return None
    
    async def set_validation_result(self, url: str, result: Dict[str, Any], is_valid: bool):
        """Cache validation result."""
        if not self.redis:
            return
        
        try:
            key = self._get_cache_key("validation", url)
            ttl = self.ttl_valid if is_valid else self.ttl_invalid
            
            # Add timestamp
            result['cached_at'] = datetime.utcnow().isoformat()
            
            await self.redis.setex(
                key,
                ttl,
                json.dumps(result)
            )
        except Exception:
            pass
    
    async def get_domain_history(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get cached domain history."""
        if not self.redis:
            return None
        
        try:
            key = self._get_cache_key("history", domain)
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        
        return None
    
    async def set_domain_history(self, domain: str, history: Dict[str, Any]):
        """Cache domain history."""
        if not self.redis:
            return
        
        try:
            key = self._get_cache_key("history", domain)
            
            # Add timestamp
            history['cached_at'] = datetime.utcnow().isoformat()
            
            await self.redis.setex(
                key,
                self.ttl_history,
                json.dumps(history)
            )
        except Exception:
            pass
    
    async def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        if not self.redis:
            return {"enabled": False}
        
        try:
            validation_keys = await self.redis.keys("url_reputation:validation:*")
            history_keys = await self.redis.keys("url_reputation:history:*")
            
            return {
                "enabled": True,
                "validation_entries": len(validation_keys),
                "history_entries": len(history_keys),
                "total_entries": len(validation_keys) + len(history_keys)
            }
        except Exception:
            return {"enabled": False}
    
    async def clear_cache(self):
        """Clear all cache entries."""
        if not self.redis:
            return
        
        try:
            keys = await self.redis.keys("url_reputation:*")
            if keys:
                await self.redis.delete(*keys)
        except Exception:
            pass