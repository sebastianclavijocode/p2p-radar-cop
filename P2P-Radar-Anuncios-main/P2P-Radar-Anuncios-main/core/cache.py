"""Simple in-memory TTL cache."""
import time
import threading
from typing import Any, Optional, Dict
from dataclasses import dataclass


@dataclass
class _Entry:
    value: Any
    expiry: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 45):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() > entry.expiry:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.ttl_seconds
        with self._lock:
            self._store[key] = _Entry(value=value, expiry=time.time() + ttl)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def remaining_ttl(self, key: str) -> Optional[float]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            remaining = entry.expiry - time.time()
            return max(0.0, remaining)
