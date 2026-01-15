from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import time
from collections import OrderedDict
from threading import RLock


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int, max_items: int):
        self.ttl = max(1, int(ttl_seconds))
        self.max_items = max(1, int(max_items))
        self._store: "OrderedDict[str, CacheItem]" = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None

            if now > item.expires_at:
                self._store.pop(key, None)
                return None

            # LRU touch
            self._store.move_to_end(key)
            return item.value

    def set(self, key: str, value: Any) -> None:
        now = time.time()
        expires_at = now + self.ttl

        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)

            self._store[key] = CacheItem(value=value, expires_at=expires_at)

            # Evict LRU if needed
            while len(self._store) > self.max_items:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            return {
                "ttl_seconds": self.ttl,
                "max_items": self.max_items,
                "current_items": len(self._store),
            }
