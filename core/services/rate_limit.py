import time
from collections import defaultdict, deque

from core.config import get_settings


class RateLimiter:
    """Sliding-window limiter keyed by client IP. Cheap and in-memory."""

    def __init__(self):
        self._hits: defaultdict[str, deque] = defaultdict(deque)

    def allow(self, client_ip: str) -> bool:
        limit = get_settings().max_events_per_ip_per_minute
        if limit <= 0:
            return True

        now = time.monotonic()
        window = self._hits[client_ip]
        cutoff = now - 60.0

        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= limit:
            return False

        window.append(now)
        return True


limiter = RateLimiter()