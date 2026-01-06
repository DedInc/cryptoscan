"""
Metric types and data classes for CryptoScan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RequestMetric:
    """Metric for a single request."""

    method: str
    endpoint: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    response_size: int = 0

    @property
    def duration_ms(self) -> float:
        """Get request duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def duration_s(self) -> float:
        """Get request duration in seconds."""
        return self.duration_ms / 1000


@dataclass
class MetricsSummary:
    """Summary of collected metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_bytes: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: float = 0.0

    # Per-method breakdown
    method_counts: Dict[str, int] = field(default_factory=dict)
    method_errors: Dict[str, int] = field(default_factory=dict)
    method_avg_times: Dict[str, float] = field(default_factory=dict)
