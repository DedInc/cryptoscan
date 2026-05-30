"""
Prometheus text-format rendering for CryptoScan metrics.

Extracted from ``MetricsCollector.export_prometheus()`` so that the
collector does not need to know about formatting details.
"""

from __future__ import annotations

from .types import MetricsSummary


def render_prometheus(summary: MetricsSummary) -> str:
    """Render *summary* as a Prometheus text exposition format string."""
    lines = [
        "# HELP cryptoscan_requests_total Total number of requests",
        "# TYPE cryptoscan_requests_total counter",
        f"cryptoscan_requests_total {summary.total_requests}",
        "",
        "# HELP cryptoscan_requests_failed_total Total number of failed requests",
        "# TYPE cryptoscan_requests_failed_total counter",
        f"cryptoscan_requests_failed_total {summary.failed_requests}",
        "",
        "# HELP cryptoscan_request_duration_ms "
        "Average request duration in milliseconds",
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
