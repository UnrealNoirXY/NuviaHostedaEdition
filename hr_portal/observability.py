import json
import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Tuple

logger = logging.getLogger("hr_portal.observability")


class InMemoryMetrics:
    def __init__(self):
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = {}
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[float]] = {}
        self._lock = threading.Lock()

    def _key(self, name: str, labels: Dict[str, str]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        return name, tuple(sorted(labels.items()))

    def increment(self, name: str, value: int = 1, **labels) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def observe(self, name: str, value: float, **labels) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._histograms.setdefault(key, []).append(value)

    def snapshot(self):
        with self._lock:
            counters = {k: v for k, v in self._counters.items()}
            histograms = {k: list(v) for k, v in self._histograms.items()}
        return counters, histograms


metrics = InMemoryMetrics()


def emit_structured_log(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str))


@contextmanager
def record_latency(metric_name: str, **labels):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        metrics.observe(metric_name, elapsed_ms, **labels)
        emit_structured_log(f"{metric_name}.observed", duration_ms=round(elapsed_ms, 2), **labels)
