"""
Global metrics instance management for CryptoScan.
"""

from __future__ import annotations

from typing import Callable, Optional

from .collector import MetricsCollector
from .types import RequestMetric

# Global metrics collector (disabled by default)
_global_metrics: Optional[MetricsCollector] = None


def get_global_metrics() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Creates one if it doesn't exist.

    Returns:
        The global MetricsCollector instance
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector(enabled=False)
    return _global_metrics


def enable_global_metrics(
    max_history: int = 1000,
    on_request_complete: Optional[Callable[[RequestMetric], None]] = None,
) -> MetricsCollector:
    """
    Enable global metrics collection.

    Args:
        max_history: Maximum request history to retain
        on_request_complete: Optional callback for each request

    Returns:
        The global MetricsCollector instance
    """
    global _global_metrics
    _global_metrics = MetricsCollector(
        max_history=max_history,
        enabled=True,
        on_request_complete=on_request_complete,
    )
    return _global_metrics


def disable_global_metrics() -> None:
    """Disable global metrics collection."""
    global _global_metrics
    if _global_metrics:
        _global_metrics.enabled = False
