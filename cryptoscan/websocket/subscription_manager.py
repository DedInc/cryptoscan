"""
WebSocket subscription management.

Handles subscription lifecycle, request ID management, and callback
organization following single responsibility principle.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..core.exceptions import CSConnectionError
from .connection_manager import WebSocketConnectionManager
from .subscription_messages import (
    build_subscribe_logs,
    build_subscribe_new_heads,
    build_subscribe_pending_transactions,
    build_unsubscribe,
)

logger = logging.getLogger(__name__)


class SubscriptionType(Enum):
    """Types of WebSocket subscriptions."""

    NEW_HEADS = "newHeads"
    LOGS = "logs"
    PENDING_TRANSACTIONS = "newPendingTransactions"


@dataclass
class SubscriptionInfo:
    """Information about a subscription for restoration."""

    subscription_type: SubscriptionType
    callback: Callable
    params: dict[str, Any] | None = None
    subscription_id: str | None = None


class WebSocketSubscriptionManager:
    """Manages WebSocket subscriptions and callbacks with automatic restoration."""

    def __init__(self, connection_manager: WebSocketConnectionManager) -> None:
        self.connection = connection_manager
        self._subscriptions: dict[str, Callable] = {}
        self._subscription_registry: list[SubscriptionInfo] = []
        self._request_id = 0
        self._lock = asyncio.Lock()

    async def _get_next_request_id(self) -> int:
        """Get next unique request ID."""
        async with self._lock:
            self._request_id += 1
            return self._request_id

    async def subscribe_new_heads(self, callback: Callable[[dict], Any]) -> str:
        """Subscribe to new block headers (EVM chains)."""
        if not self.connection.is_connected():
            await self.connection.connect()
        request_id = await self._get_next_request_id()
        subscribe_msg = build_subscribe_new_heads(request_id)
        return await self._send_and_register(
            subscribe_msg, callback, SubscriptionType.NEW_HEADS
        )

    async def subscribe_logs(
        self, addresses: list[str], callback: Callable[[dict], Any]
    ) -> str:
        """Subscribe to contract logs (EVM chains)."""
        if not self.connection.is_connected():
            await self.connection.connect()
        request_id = await self._get_next_request_id()
        subscribe_msg = build_subscribe_logs(request_id, addresses)
        subscription_id = await self._send_and_register(
            subscribe_msg, callback, SubscriptionType.LOGS
        )
        self._subscription_registry[-1].params = {"addresses": addresses}
        logger.info(f"Subscribed to logs for {len(addresses)} addresses")
        return subscription_id

    async def subscribe_pending_transactions(
        self, callback: Callable[[str], Any]
    ) -> str:
        """Subscribe to pending transactions (EVM chains)."""
        if not self.connection.is_connected():
            await self.connection.connect()
        request_id = await self._get_next_request_id()
        subscribe_msg = build_subscribe_pending_transactions(request_id)
        return await self._send_and_register(
            subscribe_msg, callback, SubscriptionType.PENDING_TRANSACTIONS
        )

    async def _send_and_register(
        self,
        msg: dict,
        callback: Callable,
        sub_type: SubscriptionType,
    ) -> str:
        """Send a subscribe message and register the subscription."""
        await self.connection.send_message(json.dumps(msg))
        response = json.loads(await self.connection.receive_message())
        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)
        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback
        self._subscription_registry.append(
            SubscriptionInfo(
                subscription_type=sub_type,
                callback=callback,
                subscription_id=subscription_id,
            )
        )
        logger.info("Subscribed to %s with ID: %s", sub_type.value, subscription_id)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription."""
        if subscription_id not in self._subscriptions:
            return
        request_id = await self._get_next_request_id()
        unsubscribe_msg = build_unsubscribe(request_id, subscription_id)
        await self.connection.send_message(json.dumps(unsubscribe_msg))
        del self._subscriptions[subscription_id]
        logger.info(f"Unsubscribed from {subscription_id}")

    async def handle_subscription_message(self, data: dict) -> bool:
        """Handle incoming subscription message. Returns True if handled."""
        if "method" not in data or data["method"] != "eth_subscription":
            return False
        params = data.get("params", {})
        subscription_id = params.get("subscription")
        result = params.get("result")
        if subscription_id in self._subscriptions and result is not None:
            callback = self._subscriptions[subscription_id]
            if asyncio.iscoroutinefunction(callback):
                await callback(result)
            else:
                callback(result)
            return True
        return False

    def get_subscription_count(self) -> int:
        """Get number of active subscriptions."""
        return len(self._subscriptions)

    def clear_subscriptions(self) -> None:
        """Clear active subscriptions; registry preserved for restoration."""
        self._subscriptions.clear()

    def clear_registry(self) -> None:
        """Clear the subscription registry completely."""
        self._subscriptions.clear()
        self._subscription_registry.clear()

    def get_registry_count(self) -> int:
        """Get number of subscriptions in the registry (for restoration)."""
        return len(self._subscription_registry)

    async def restore_subscriptions(self) -> int:
        """Restore all subscriptions after a reconnection."""
        if not self._subscription_registry:
            logger.debug("No subscriptions to restore")
            return 0
        registry_copy = list(self._subscription_registry)
        self._subscription_registry.clear()
        restored_count = 0
        failed_subscriptions: list[SubscriptionInfo] = []
        for info in registry_copy:
            new_id = await self._restore_single(info)
            if new_id is not None:
                logger.info(
                    "Restored %s subscription: %s", info.subscription_type.value, new_id
                )
                restored_count += 1
            else:
                failed_subscriptions.append(info)
        self._subscription_registry.extend(failed_subscriptions)
        if restored_count > 0:
            logger.info(f"Successfully restored {restored_count} subscription(s)")
        if failed_subscriptions:
            logger.warning(
                f"Failed to restore {len(failed_subscriptions)} subscription(s)"
            )
        return restored_count

    async def _restore_single(self, info: SubscriptionInfo) -> str | None:
        """Restore a single subscription, returning the new id or ``None``."""
        from .subscription_restore import restore_subscription

        return await restore_subscription(info, self)
