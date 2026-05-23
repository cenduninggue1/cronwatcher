"""Lightweight in-process metrics collector for cronwatcher."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Counter:
    name: str
    value: int = 0

    def increment(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class Gauge:
    name: str
    value: float = 0.0

    def set(self, v: float) -> None:
        self.value = v


@dataclass
class MetricsSnapshot:
    counters: Dict[str, int] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=_utcnow)


class MetricsRegistry:
    """Thread-safe registry for counters and gauges."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}

    def counter(self, name: str) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name)
            return self._counters[name]

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name)
            return self._gauges[name]

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(
                counters={k: v.value for k, v in self._counters.items()},
                gauges={k: v.value for k, v in self._gauges.items()},
            )

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()


# Module-level default registry
_registry: Optional[MetricsRegistry] = None


def get_registry() -> MetricsRegistry:
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


def format_snapshot(snap: MetricsSnapshot) -> List[str]:
    """Return human-readable lines for a metrics snapshot."""
    lines: List[str] = [f"Metrics collected at {snap.collected_at.isoformat()}"]
    for name, value in sorted(snap.counters.items()):
        lines.append(f"  counter {name}: {value}")
    for name, value in sorted(snap.gauges.items()):
        lines.append(f"  gauge   {name}: {value:.4f}")
    return lines
