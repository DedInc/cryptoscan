"""
Metrics and telemetry for CryptoScan.

This module re-exports from the metrics package for backward compatibility.
"""

from .metrics import (
    MetricsCollector,
    MetricsSummary,
    RequestMetric,
    disable_global_metrics,
    enable_global_metrics,
    get_global_metrics,
)

__all__ = [
    "RequestMetric",
    "MetricsSummary",
    "MetricsCollector",
    "get_global_metrics",
    "enable_global_metrics",
    "disable_global_metrics",
]
