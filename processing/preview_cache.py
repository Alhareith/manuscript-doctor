"""Per-worker, byte-bounded caches for immutable preview data only.

Never retain full-resolution images. File identity includes mtime/size/inode;
replaced files and independent Flask application instances cannot share entries.
A per-key single flight avoids duplicate decoding under concurrent slider requests.
"""
from collections import OrderedDict
from pathlib import Path
from threading import Condition
from time import monotonic


def file_key(path):
    path = Path(path).resolve()
    stat = path.stat()
    return (str(path), stat.st_ino, stat.st_size, stat.st_mtime_ns)


class PreviewCache:
    def __init__(self, max_bytes=32 * 1024 * 1024, ttl=300, max_entries=64):
        self.max_bytes = max_bytes
        self.ttl = ttl
        self.max_entries = max_entries
        self._entries = OrderedDict()
        self._pending = set()
        self._condition = Condition()
        self.bytes = 0

    def get_or_create(self, key, factory, size):
        with self._condition:
            while key in self._pending:
                self._condition.wait()
            now = monotonic()
            for stale in [k for k, (_, _, expires) in self._entries.items() if expires <= now]:
                _, weight, _ = self._entries.pop(stale)
                self.bytes -= weight
            if key in self._entries:
                value, _, _ = self._entries[key]
                self._entries.move_to_end(key)
                return value
            self._pending.add(key)
        try:
            value = factory()
            weight = size(value)
            with self._condition:
                if value is not None and 0 < weight <= self.max_bytes:
                    while self._entries and (self.bytes + weight > self.max_bytes or len(self._entries) >= self.max_entries):
                        _, (_, old_weight, _) = self._entries.popitem(last=False)
                        self.bytes -= old_weight
                    self._entries[key] = (value, weight, monotonic() + self.ttl)
                    self.bytes += weight
            return value
        finally:
            with self._condition:
                self._pending.discard(key)
                self._condition.notify_all()
