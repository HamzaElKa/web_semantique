from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import time
from collections import OrderedDict

@dataclass
class CacheItem:
    value: Any
    expires_at: float

class TTLCache:
    def __init__(self, ttl_seconds: int, max_items: int):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: "OrderedDict[str, CacheItem]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        if time.time() > item.expires_at:
            self._store.pop(key, None)
            return None
        # LRU touch
        self._store.move_to_end(key)
        return item.value

    def set(self, key: str, value: Any) -> None:
        # Evict if needed
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = CacheItem(value=value, expires_at=time.time() + self.ttl)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)
