"""Callback dispatch helpers for payment and error events."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from ..core.models import ErrorEvent, PaymentEvent, PaymentInfo

logger = logging.getLogger(__name__)


async def emit_payment_event(
    payment_info: PaymentInfo,
    monitor_id: str,
    network_name: str,
    payment_callbacks: list[Callable],
) -> None:
    """Build a PaymentEvent and dispatch it to all registered callbacks."""
    event = PaymentEvent(
        payment_info=payment_info,
        monitor_id=monitor_id,
        network=network_name,
    )

    for callback in payment_callbacks:
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"Error in payment callback: {e}")


async def emit_error_event(
    error: Exception,
    monitor_id: str,
    network_name: str,
    error_callbacks: list[Callable],
) -> None:
    """Build an ErrorEvent and dispatch it to all registered callbacks."""
    event = ErrorEvent(
        error=error,
        monitor_id=monitor_id,
        network=network_name,
    )

    for callback in error_callbacks:
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"Error in error callback: {e}")
