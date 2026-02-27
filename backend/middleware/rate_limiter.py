"""Redis-based rate limiting middleware."""

import logging
import time

import redis
from flask import Flask, request

from backend.middleware.error_handlers import APIError
from config.settings import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based sliding window rate limiter.

    Limits requests per IP address using a Redis sorted set.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Initialize the rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis = None

    def _get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                password=settings.redis.password,
                decode_responses=True,
                socket_connect_timeout=2,
            )
        return self._redis

    def check_rate_limit(self, key: str) -> bool:
        """
        Check and record a request against the rate limit.

        Args:
            key: Rate limit key (e.g., IP address)

        Returns:
            True if request is allowed, False if rate limited
        """
        try:
            r = self._get_redis()
            now = time.time()
            pipe = r.pipeline()
            redis_key = f"rate_limit:{key}"

            pipe.zremrangebyscore(redis_key, 0, now - self.window_seconds)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, self.window_seconds)

            results = pipe.execute()
            request_count = results[2]

            return request_count <= self.max_requests
        except redis.ConnectionError:
            logger.warning("Redis unavailable for rate limiting, allowing request")
            return True


def register_rate_limiter(app: Flask) -> None:
    """
    Register rate limiting middleware on the Flask app.

    Args:
        app: Flask application instance
    """
    limiter = RateLimiter(max_requests=120, window_seconds=60)

    @app.before_request
    def check_rate_limit():
        if request.path == "/api/health":
            return None

        client_ip = request.remote_addr or "0.0.0.0"
        if not limiter.check_rate_limit(client_ip):
            raise APIError("Rate limit exceeded", status_code=429)
