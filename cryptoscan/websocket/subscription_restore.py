"""
Subscription restoration logic for ``WebSocketSubscriptionManager``.

Extracted here so that ``subscription_manager.py`` stays focused on
subscription lifecycle management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .subscription_manager import SubscriptionType

if TYPE_CHECKING:
    from .subscription_manager import SubscriptionInfo, WebSocketSubscriptionManager

logger = logging.getLogger(__name__)


async def restore_subscription(
    info: SubscriptionInfo,
    manager: WebSocketSubscriptionManager,
) -> str | None:
    """Re-subscribe *info* via the appropriate method on *manager*.

    Returns the new subscription ID on success, or ``None`` on failure
    (the error is logged but **not** raised).
    """
    try:
        if info.subscription_type == SubscriptionType.NEW_HEADS:
            return await manager.subscribe_new_heads(info.callback)

        if info.subscription_type == SubscriptionType.LOGS:
            addresses = info.params.get("addresses", []) if info.params else []
            return await manager.subscribe_logs(addresses, info.callback)

        if info.subscription_type == SubscriptionType.PENDING_TRANSACTIONS:
            return await manager.subscribe_pending_transactions(info.callback)

        logger.warning(
            "Unknown subscription type for restoration: %s",
            info.subscription_type,
        )
        return None
    except Exception:
        logger.error(
            "Failed to restore %s subscription",
            info.subscription_type.value,
            exc_info=True,
        )
        return None
