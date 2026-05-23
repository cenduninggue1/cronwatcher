"""Tests for cronwatcher.metrics."""

import threading
import pytest

from cronwatcher.metrics import (
    Counter,
    Gauge,
    MetricsRegistry,
    MetricsSnapshot,
    format_snapshot,
    get_registry,
)


@pytest.fixture(autouse=True)
def fresh_registry():
    """Ensure a clean registry for every test."""
    reg = get_registry()
    reg.reset()
    yield reg
    reg.reset()


def test_counter_increments():
    reg = MetricsRegistry()
    c = reg.counter("jobs.run")
    c.increment()
    c.increment(3)
    assert c.value == 4


def test_counter_same_name_returns_same_object():
    reg = MetricsRegistry()
    c1 = reg.counter("x")
    c2 = reg.counter("x")
    assert c1 is c2


def test_gauge_set():
    reg = MetricsRegistry()
    g = reg.gauge("last_duration")
    g.set(3.14)
    assert g.value == pytest.approx(3.14)


def test_gauge_same_name_returns_same_object():
    reg = MetricsRegistry()
    g1 = reg.gauge("y")
    g2 = reg.gauge("y")
    assert g1 is g2


def test_snapshot_captures_values():
    reg = MetricsRegistry()
    reg.counter("a").increment(5)
    reg.gauge("b").set(2.5)
    snap = reg.snapshot()
    assert snap.counters == {"a": 5}
    assert snap.gauges == {"b": pytest.approx(2.5)}


def test_snapshot_is_copy():
    reg = MetricsRegistry()
    reg.counter("a").increment(1)
    snap = reg.snapshot()
    reg.counter("a").increment(10)
    assert snap.counters["a"] == 1  # snapshot not mutated


def test_reset_clears_all():
    reg = MetricsRegistry()
    reg.counter("a").increment()
    reg.gauge("b").set(1.0)
    reg.reset()
    snap = reg.snapshot()
    assert snap.counters == {}
    assert snap.gauges == {}


def test_thread_safety():
    reg = MetricsRegistry()
    c = reg.counter("threads")

    def worker():
        for _ in range(100):
            c.increment()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert c.value == 1000


def test_format_snapshot_contains_metric_names():
    reg = MetricsRegistry()
    reg.counter("jobs.failed").increment(2)
    reg.gauge("uptime").set(60.0)
    snap = reg.snapshot()
    lines = format_snapshot(snap)
    joined = "\n".join(lines)
    assert "jobs.failed" in joined
    assert "uptime" in joined
    assert "2" in joined


def test_get_registry_returns_singleton():
    r1 = get_registry()
    r2 = get_registry()
    assert r1 is r2
