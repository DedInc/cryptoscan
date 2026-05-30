"""
MetricsCollector for CryptoScan performance monitoring.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from threading import Lock
from types import TracebackType
from typing import Any

from .prometheus import render_prometheus
from .summary import compute_summary
from .types import MetricsSummary, RequestMetric

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates performance metrics for CryptoScan operations."""

    def __init__(
        self,
        max_history: int = 1000,
        enabled: bool = True,
        on_request_complete: Callable[[RequestMetric], None] | None = None,
    ) -> None:
        self._enabled = enabled
        self._max_history = max_history
        self._on_request_complete = on_request_complete
        self._lock = Lock()
        self._start_time = time.monotonic()
        self._requests: list[RequestMetric] = []
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._total_response_bytes = 0
        self._total_response_time_ms = 0.0
        self._method_counts: dict[str, int] = {}
        self._method_errors: dict[str, int] = {}
        self._method_total_times: dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable metrics collection."""
        self._enabled = value

    def reset(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self._start_time = time.monotonic()
            self._requests.clear()
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_response_bytes = 0
            self._total_response_time_ms = 0.0
            self._method_counts.clear()
            self._method_errors.clear()
            self._method_total_times.clear()

    @asynccontextmanager
    async def track_request(
        self, method: str, endpoint: str
    ) -> AsyncIterator[RequestMetric]:
        """Async context manager to track a request."""
        if not self._enabled:
            yield RequestMetric(method=method, endpoint=endpoint, start_time=0)
            return

        metric = RequestMetric(
            method=method, endpoint=endpoint, start_time=time.monotonic()
        )
        try:
            yield metric
            metric.success = True
        except Exception as e:
            metric.success = False
            metric.error = str(e)
            raise
        finally:
            metric.end_time = time.monotonic()
            self._record_metric(metric)

    def track_request_sync(self, method: str, endpoint: str) -> _SyncRequestTracker:
        """Sync context manager to track a request."""
        return _SyncRequestTracker(self, method, endpoint)

    def record_request(
        self,
        method: str,
        endpoint: str,
        duration_ms: float,
        success: bool = True,
        error: str | None = None,
        response_size: int = 0,
    ) -> None:
        """Manually record a request metric."""
        if not self._enabled:
            return
        metric = RequestMetric(
            method=method,
            endpoint=endpoint,
            start_time=time.monotonic() - (duration_ms / 1000),
            end_time=time.monotonic(),
            success=success,
            error=error,
            response_size=response_size,
        )
        self._record_metric(metric)

    def _record_metric(self, metric: RequestMetric) -> None:
        """Internal method to record a metric."""
        with self._lock:
            self._requests.append(metric)
            if len(self._requests) > self._max_history:
                self._requests.pop(0)
            self._total_requests += 1
            if metric.success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1
            self._total_response_bytes += metric.response_size
            self._total_response_time_ms += metric.duration_ms
            method = metric.method
            self._method_counts[method] = self._method_counts.get(method, 0) + 1
            if not metric.success:
                self._method_errors[method] = self._method_errors.get(method, 0) + 1
            self._method_total_times[method] = (
                self._method_total_times.get(method, 0.0) + metric.duration_ms
            )
        if self._on_request_complete:
            try:
                self._on_request_complete(metric)
            except Exception as e:
                logger.warning(f"Metrics callback error: {e}")

    def get_summary(self) -> MetricsSummary:
        """Get a summary of all collected metrics."""
        with self._lock:
            return compute_summary(
                requests=list(self._requests),
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
                total_response_bytes=self._total_response_bytes,
                total_response_time_ms=self._total_response_time_ms,
                method_counts=dict(self._method_counts),
                method_errors=dict(self._method_errors),
                method_total_times=dict(self._method_total_times),
                uptime=time.monotonic() - self._start_time,
            )

    def get_recent_requests(self, limit: int = 10) -> list[RequestMetric]:
        """Get the most recent request metrics."""
        with self._lock:
            return list(self._requests[-limit:])

    def get_errors(self, limit: int = 10) -> list[RequestMetric]:
        """Get recent failed requests."""
        with self._lock:
            return [r for r in self._requests if not r.success][-limit:]

    def get_method_stats(self, method: str) -> dict[str, Any]:
        """Get statistics for a specific method."""
        with self._lock:
            count = self._method_counts.get(method, 0)
            errors = self._method_errors.get(method, 0)
            total_time = self._method_total_times.get(method, 0.0)
            return {
                "method": method,
                "total_calls": count,
                "errors": errors,
                "error_rate": errors / count if count > 0 else 0.0,
                "avg_time_ms": total_time / count if count > 0 else 0.0,
                "total_time_ms": total_time,
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        return render_prometheus(self.get_summary())

    def __repr__(self) -> str:
        summary = self.get_summary()
        return (
            f"MetricsCollector(requests={summary.total_requests}, "
            f"errors={summary.failed_requests}, "
            f"avg_time={summary.avg_response_time_ms:.1f}ms, "
            f"enabled={self._enabled})"
        )


class _SyncRequestTracker:
    """Sync context manager for tracking requests."""

    def __init__(self, collector: MetricsCollector, method: str, endpoint: str) -> None:
        self._collector = collector
        self._method = method
        self._endpoint = endpoint
        self._metric: RequestMetric | None = None

    def __enter__(self) -> RequestMetric:
        if not self._collector.enabled:
            self._metric = RequestMetric(
                method=self._method, endpoint=self._endpoint, start_time=0
            )
            return self._metric
        self._metric = RequestMetric(
            method=self._method, endpoint=self._endpoint, start_time=time.monotonic()
        )
        return self._metric

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if self._metric and self._collector.enabled:
            self._metric.end_time = time.monotonic()
            if exc_type is not None:
                self._metric.success = False
                self._metric.error = str(exc_val)
            self._collector._record_metric(self._metric)
        return False
