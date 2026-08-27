import threading
import time
from typing import Dict, Any

class TTLCache:
    def __init__(self, ttl_seconds: int = 7200, maxsize: int = 200):
        self._store: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.ttl = ttl_seconds
        self.maxsize = maxsize

    def get(self, key: str):
        with self._lock:
            if key not in self._store:
                return None
            val, ts = self._store[key]
            if time.time() - ts > self.ttl:
                del self._store[key]
                return None
            return val

    def set(self, key: str, val: Any):
        with self._lock:
            if len(self._store) >= self.maxsize:
                oldest = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest]
            self._store[key] = (val, time.time())

    def contains(self, key: str) -> bool:
        return self.get(key) is not None
