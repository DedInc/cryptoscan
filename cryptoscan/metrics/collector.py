"""
MetricsCollector for CryptoScan performance monitoring.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from .types import MetricsSummary, RequestMetric

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and aggregates performance metrics for CryptoScan operations.

    Features:
    - Request counting and timing
    - Error rate tracking
    - Per-method statistics
    - Configurable history retention
    - Thread-safe operations
    - Optional callbacks for real-time monitoring

    Usage:
        >>> collector = MetricsCollector()
        >>>
        >>> # Track a request manually
        >>> with collector.track_request("eth_blockNumber", "https://rpc.example.com"):
        ...     response = await make_request()
        >>>
        >>> # Get summary
        >>> summary = collector.get_summary()
        >>> print(f"Total requests: {summary.total_requests}")
        >>> print(f"Error rate: {summary.error_rate:.2%}")
    """

    def __init__(
        self,
        max_history: int = 1000,
        enabled: bool = True,
        on_request_complete: Optional[Callable[[RequestMetric], None]] = None,
    ):
        """
        Initialize MetricsCollector.

        Args:
            max_history: Maximum number of request metrics to retain
            enabled: Whether metrics collection is enabled
            on_request_complete: Optional callback called after each request
        """
        self._enabled = enabled
        self._max_history = max_history
        self._on_request_complete = on_request_complete

        self._lock = Lock()
        self._start_time = time.monotonic()
        self._requests: List[RequestMetric] = []

        # Counters (for efficiency, track separately from history)
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._total_response_bytes = 0
        self._total_response_time_ms = 0.0

        # Per-method counters
        self._method_counts: Dict[str, int] = {}
        self._method_errors: Dict[str, int] = {}
        self._method_total_times: Dict[str, float] = {}

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
    async def track_request(self, method: str, endpoint: str):
        """
        Async context manager to track a request.

        Args:
            method: The RPC method or API endpoint being called
            endpoint: The base URL of the endpoint

        Yields:
            RequestMetric: The metric object (can be modified to add response_size)

        Example:
            >>> async with collector.track_request("eth_getBalance", "https://rpc.example.com") as metric:
            ...     response = await client.call("eth_getBalance", [address])
            ...     metric.response_size = len(response)
        """
        if not self._enabled:
            yield RequestMetric(method=method, endpoint=endpoint, start_time=0)
            return

        metric = RequestMetric(
            method=method,
            endpoint=endpoint,
            start_time=time.monotonic(),
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

    def track_request_sync(self, method: str, endpoint: str):
        """
        Sync context manager to track a request.

        Args:
            method: The RPC method or API endpoint being called
            endpoint: The base URL of the endpoint
        """
        return _SyncRequestTracker(self, method, endpoint)

    def record_request(
        self,
        method: str,
        endpoint: str,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        response_size: int = 0,
    ) -> None:
        """
        Manually record a request metric.

        Args:
            method: The RPC method or API endpoint
            endpoint: The base URL
            duration_ms: Request duration in milliseconds
            success: Whether the request succeeded
            error: Error message if failed
            response_size: Response size in bytes
        """
        if not self._enabled:
            return

        start_time = time.monotonic() - (duration_ms / 1000)
        metric = RequestMetric(
            method=method,
            endpoint=endpoint,
            start_time=start_time,
            end_time=time.monotonic(),
            success=success,
            error=error,
            response_size=response_size,
        )
        self._record_metric(metric)

    def _record_metric(self, metric: RequestMetric) -> None:
        """Internal method to record a metric."""
        with self._lock:
            # Add to history (with size limit)
            self._requests.append(metric)
            if len(self._requests) > self._max_history:
                self._requests.pop(0)

            # Update counters
            self._total_requests += 1
            if metric.success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

            self._total_response_bytes += metric.response_size
            self._total_response_time_ms += metric.duration_ms

            # Update per-method counters
            method = metric.method
            self._method_counts[method] = self._method_counts.get(method, 0) + 1
            if not metric.success:
                self._method_errors[method] = self._method_errors.get(method, 0) + 1
            self._method_total_times[method] = (
                self._method_total_times.get(method, 0.0) + metric.duration_ms
            )

        # Call callback if provided
        if self._on_request_complete:
            try:
                self._on_request_complete(metric)
            except Exception as e:
                logger.warning(f"Metrics callback error: {e}")

    def get_summary(self) -> MetricsSummary:
        """
        Get a summary of all collected metrics.

        Returns:
            MetricsSummary with aggregated statistics
        """
        with self._lock:
            uptime = time.monotonic() - self._start_time

            # Calculate averages
            avg_time = 0.0
            if self._total_requests > 0:
                avg_time = self._total_response_time_ms / self._total_requests

            # Calculate min/max from history
            min_time = 0.0
            max_time = 0.0
            if self._requests:
                times = [r.duration_ms for r in self._requests if r.end_time]
                if times:
                    min_time = min(times)
                    max_time = max(times)

            # Calculate requests per second
            rps = 0.0
            if uptime > 0:
                rps = self._total_requests / uptime

            # Calculate error rate
            error_rate = 0.0
            if self._total_requests > 0:
                error_rate = self._failed_requests / self._total_requests

            # Calculate per-method averages
            method_avg_times = {}
            for method, total_time in self._method_total_times.items():
                count = self._method_counts.get(method, 1)
                method_avg_times[method] = total_time / count

            return MetricsSummary(
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
                total_response_bytes=self._total_response_bytes,
                avg_response_time_ms=avg_time,
                min_response_time_ms=min_time,
                max_response_time_ms=max_time,
                requests_per_second=rps,
                error_rate=error_rate,
                uptime_seconds=uptime,
                method_counts=dict(self._method_counts),
                method_errors=dict(self._method_errors),
                method_avg_times=method_avg_times,
            )

    def get_recent_requests(self, limit: int = 10) -> List[RequestMetric]:
        """
        Get the most recent request metrics.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of recent RequestMetric objects
        """
        with self._lock:
            return list(self._requests[-limit:])

    def get_errors(self, limit: int = 10) -> List[RequestMetric]:
        """
        Get recent failed requests.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of failed RequestMetric objects
        """
        with self._lock:
            errors = [r for r in self._requests if not r.success]
            return errors[-limit:]

    def get_method_stats(self, method: str) -> Dict[str, Any]:
        """
        Get statistics for a specific method.

        Args:
            method: The method name to get stats for

        Returns:
            Dictionary with method-specific statistics
        """
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
        """
        Export metrics in Prometheus format.

        Returns:
            String with Prometheus-formatted metrics
        """
        summary = self.get_summary()
        lines = [
            "# HELP cryptoscan_requests_total Total number of requests",
            "# TYPE cryptoscan_requests_total counter",
            f"cryptoscan_requests_total {summary.total_requests}",
            "",
            "# HELP cryptoscan_requests_failed_total Total number of failed requests",
            "# TYPE cryptoscan_requests_failed_total counter",
            f"cryptoscan_requests_failed_total {summary.failed_requests}",
            "",
            "# HELP cryptoscan_request_duration_ms Average request duration in milliseconds",
            "# TYPE cryptoscan_request_duration_ms gauge",
            f"cryptoscan_request_duration_ms {summary.avg_response_time_ms:.2f}",
            "",
            "# HELP cryptoscan_requests_per_second Current requests per second",
            "# TYPE cryptoscan_requests_per_second gauge",
            f"cryptoscan_requests_per_second {summary.requests_per_second:.4f}",
            "",
            "# HELP cryptoscan_error_rate Current error rate",
            "# TYPE cryptoscan_error_rate gauge",
            f"cryptoscan_error_rate {summary.error_rate:.4f}",
            "",
            "# HELP cryptoscan_uptime_seconds Collector uptime in seconds",
            "# TYPE cryptoscan_uptime_seconds gauge",
            f"cryptoscan_uptime_seconds {summary.uptime_seconds:.2f}",
        ]

        # Add per-method metrics
        if summary.method_counts:
            lines.extend(
                [
                    "",
                    "# HELP cryptoscan_method_requests_total Requests per method",
                    "# TYPE cryptoscan_method_requests_total counter",
                ]
            )
            for method, count in summary.method_counts.items():
                lines.append(
                    f'cryptoscan_method_requests_total{{method="{method}"}} {count}'
                )

        return "\n".join(lines)

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

    def __init__(self, collector: MetricsCollector, method: str, endpoint: str):
        self._collector = collector
        self._method = method
        self._endpoint = endpoint
        self._metric: Optional[RequestMetric] = None

    def __enter__(self) -> RequestMetric:
        if not self._collector.enabled:
            self._metric = RequestMetric(
                method=self._method, endpoint=self._endpoint, start_time=0
            )
            return self._metric

        self._metric = RequestMetric(
            method=self._method,
            endpoint=self._endpoint,
            start_time=time.monotonic(),
        )
        return self._metric

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._metric and self._collector.enabled:
            self._metric.end_time = time.monotonic()
            if exc_type is not None:
                self._metric.success = False
                self._metric.error = str(exc_val)
            self._collector._record_metric(self._metric)
        return False
