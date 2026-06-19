import os
import time
import logging
import threading
import json
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("adsphere.cache")

class LocalCache:
    """A thread-safe, in-memory cache that emulates Redis operations with TTL expiration."""
    def __init__(self):
        self._cache = {}
        self._expires = {}
        self._lock = threading.Lock()
        logger.info("Initializing Local Cache (fallback mode)")

    def _is_expired(self, key):
        if key not in self._expires:
            return False
        if self._expires[key] is None:
            return False
        if time.time() > self._expires[key]:
            return True
        return False

    def _clean_expired(self, key):
        if self._is_expired(key):
            self._cache.pop(key, None)
            self._expires.pop(key, None)
            return True
        return False

    def get(self, key):
        with self._lock:
            self._clean_expired(key)
            val = self._cache.get(key)
            if val is not None and isinstance(val, (dict, list)):
                return json.dumps(val)
            return val

    def set(self, key, value, ex=None):
        with self._lock:
            self._cache[key] = value
            if ex is not None:
                self._expires[key] = time.time() + float(ex)
            else:
                self._expires[key] = None
            return True

    def delete(self, key):
        with self._lock:
            a = key in self._cache
            self._cache.pop(key, None)
            self._expires.pop(key, None)
            return a

    def incr(self, key, amount=1):
        with self._lock:
            self._clean_expired(key)
            val = self._cache.get(key, 0)
            try:
                new_val = int(val) + amount
            except (ValueError, TypeError):
                new_val = amount
            self._cache[key] = new_val
            return new_val

    def incr_by_float(self, key, amount=1.0):
        with self._lock:
            self._clean_expired(key)
            val = self._cache.get(key, 0.0)
            try:
                new_val = float(val) + amount
            except (ValueError, TypeError):
                new_val = amount
            self._cache[key] = new_val
            return new_val


class RedisCacheManager:
    """Wrapper that tries to use Redis and falls back to LocalCache on failure."""
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = None
        self.use_fallback = True
        
        # Try importing redis client
        try:
            import redis
            logger.info(f"Attempting to connect to Redis at: {self.redis_url}")
            self.client = redis.from_url(self.redis_url, socket_connect_timeout=2.0, decode_responses=True)
            # Test connection
            self.client.ping()
            self.use_fallback = False
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Falling back to In-Memory Cache.")
            self.client = LocalCache()
            self.use_fallback = True

    def get(self, key):
        try:
            if self.use_fallback:
                return self.client.get(key)
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}. Falling back to mock call.")
            return None

    def set(self, key, value, expire_seconds=None):
        try:
            if self.use_fallback:
                return self.client.set(key, value, ex=expire_seconds)
            return self.client.set(key, value, ex=expire_seconds)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key):
        try:
            if self.use_fallback:
                return self.client.delete(key)
            return self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def incr(self, key, amount=1):
        try:
            if self.use_fallback:
                return self.client.incr(key, amount)
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return amount

    def incr_by_float(self, key, amount=1.0):
        try:
            if self.use_fallback:
                return self.client.incr_by_float(key, amount)
            # Redis command is incrbyfloat
            return self.client.incrbyfloat(key, amount)
        except Exception as e:
            logger.error(f"Redis incr_by_float error: {e}")
            return amount

# Global cache instance
cache = RedisCacheManager()
