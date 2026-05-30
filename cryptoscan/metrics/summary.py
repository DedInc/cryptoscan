"""
Pure-function computation of metrics summaries.

Extracted from ``MetricsCollector.get_summary()`` so that the
collector can focus on recording and the summary calculation
can be tested independently.
"""

from __future__ import annotations

from .types import MetricsSummary, RequestMetric


def compute_summary(
    *,
    requests: list[RequestMetric],
    total_requests: int,
    successful_requests: int,
    failed_requests: int,
    total_response_bytes: int,
    total_response_time_ms: float,
    method_counts: dict[str, int],
    method_errors: dict[str, int],
    method_total_times: dict[str, float],
    uptime: float,
) -> MetricsSummary:
    """Compute an aggregated ``MetricsSummary`` from raw snapshot values.

    All parameters are keyword-only for clarity and future-proofing.
    """
    avg_time = 0.0
    if total_requests > 0:
        avg_time = total_response_time_ms / total_requests

    min_time = 0.0
    max_time = 0.0
    if requests:
        times = [r.duration_ms for r in requests if r.end_time]
        if times:
            min_time = min(times)
            max_time = max(times)

    rps = 0.0
    if uptime > 0:
        rps = total_requests / uptime

    error_rate = 0.0
    if total_requests > 0:
        error_rate = failed_requests / total_requests

    method_avg_times: dict[str, float] = {}
    for method, total_time in method_total_times.items():
        count = method_counts.get(method, 1)
        method_avg_times[method] = total_time / count

    return MetricsSummary(
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        total_response_bytes=total_response_bytes,
        avg_response_time_ms=avg_time,
        min_response_time_ms=min_time,
        max_response_time_ms=max_time,
        requests_per_second=rps,
        error_rate=error_rate,
        uptime_seconds=uptime,
        method_counts=dict(method_counts),
        method_errors=dict(method_errors),
        method_avg_times=method_avg_times,
    )
