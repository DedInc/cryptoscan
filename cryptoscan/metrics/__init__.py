"""
Metrics and telemetry for CryptoScan.

Provides optional performance monitoring and statistics collection
for debugging, optimization, and observability.
"""

from .collector import MetricsCollector
from .global_metrics import (
    disable_global_metrics,
    enable_global_metrics,
    get_global_metrics,
)
from .types import MetricsSummary, RequestMetric

__all__ = [
    "RequestMetric",
    "MetricsSummary",
    "MetricsCollector",
    "get_global_metrics",
    "enable_global_metrics",
    "disable_global_metrics",
]
