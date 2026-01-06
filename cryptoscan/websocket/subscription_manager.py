"""
WebSocket subscription management

Handles subscription lifecycle, request ID management, and callback organization
following single responsibility principle.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Callable, Any, List, Optional

from .connection_manager import WebSocketConnectionManager
from ..exceptions import ConnectionError as CSConnectionError


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
    params: Optional[Dict[str, Any]] = None  # Additional params like addresses for logs
    subscription_id: Optional[str] = None  # The actual subscription ID from the server


class WebSocketSubscriptionManager:
    """Manages WebSocket subscriptions and callbacks with automatic restoration."""

    def __init__(self, connection_manager: WebSocketConnectionManager):
        self.connection = connection_manager
        self._subscriptions: Dict[str, Callable] = {}  # subscription_id -> callback
        self._subscription_registry: List[SubscriptionInfo] = []  # For restoration
        self._request_id = 0
        self._lock = asyncio.Lock()

    async def _get_next_request_id(self) -> int:
        """Get next unique request ID"""
        async with self._lock:
            self._request_id += 1
            return self._request_id

    async def subscribe_new_heads(self, callback: Callable[[dict], Any]) -> str:
        """
        Subscribe to new block headers (EVM chains)

        Args:
            callback: Async function to call with each new block header

        Returns:
            Subscription ID
        """
        if not self.connection.is_connected():
            await self.connection.connect()

        request_id = await self._get_next_request_id()

        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "eth_subscribe",
            "params": ["newHeads"],
        }

        await self.connection.send_message(json.dumps(subscribe_msg))
        response = json.loads(await self.connection.receive_message())

        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)

        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback

        # Register for restoration
        info = SubscriptionInfo(
            subscription_type=SubscriptionType.NEW_HEADS,
            callback=callback,
            subscription_id=subscription_id,
        )
        self._subscription_registry.append(info)

        logger.info(f"Subscribed to newHeads with ID: {subscription_id}")
        return subscription_id

    async def subscribe_logs(
        self, addresses: list[str], callback: Callable[[dict], Any]
    ) -> str:
        """
        Subscribe to contract logs (EVM chains)

        Args:
            addresses: List of contract addresses to monitor
            callback: Async function to call with each log event

        Returns:
            Subscription ID
        """
        if not self.connection.is_connected():
            await self.connection.connect()

        request_id = await self._get_next_request_id()

        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "eth_subscribe",
            "params": ["logs", {"address": addresses}],
        }

        await self.connection.send_message(json.dumps(subscribe_msg))
        response = json.loads(await self.connection.receive_message())

        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)

        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback

        # Register for restoration
        info = SubscriptionInfo(
            subscription_type=SubscriptionType.LOGS,
            callback=callback,
            params={"addresses": addresses},
            subscription_id=subscription_id,
        )
        self._subscription_registry.append(info)

        logger.info(f"Subscribed to logs for {len(addresses)} addresses")
        return subscription_id

    async def subscribe_pending_transactions(
        self, callback: Callable[[str], Any]
    ) -> str:
        """
        Subscribe to pending transactions (EVM chains)

        Args:
            callback: Async function to call with each transaction hash

        Returns:
            Subscription ID
        """
        if not self.connection.is_connected():
            await self.connection.connect()

        request_id = await self._get_next_request_id()

        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "eth_subscribe",
            "params": ["newPendingTransactions"],
        }

        await self.connection.send_message(json.dumps(subscribe_msg))
        response = json.loads(await self.connection.receive_message())

        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)

        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback

        # Register for restoration
        info = SubscriptionInfo(
            subscription_type=SubscriptionType.PENDING_TRANSACTIONS,
            callback=callback,
            subscription_id=subscription_id,
        )
        self._subscription_registry.append(info)

        logger.info("Subscribed to pending transactions")
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription"""
        if subscription_id not in self._subscriptions:
            return

        request_id = await self._get_next_request_id()

        unsubscribe_msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "eth_unsubscribe",
            "params": [subscription_id],
        }

        await self.connection.send_message(json.dumps(unsubscribe_msg))
        del self._subscriptions[subscription_id]
        logger.info(f"Unsubscribed from {subscription_id}")

    async def handle_subscription_message(self, data: dict) -> bool:
        """
        Handle incoming subscription message

        Args:
            data: Parsed JSON message

        Returns:
            True if message was handled, False otherwise
        """
        if "method" not in data or data["method"] != "eth_subscription":
            return False

        params = data.get("params", {})
        subscription_id = params.get("subscription")
        result = params.get("result")

        if subscription_id in self._subscriptions and result is not None:
            callback = self._subscriptions[subscription_id]

            # Call callback (handle both sync and async)
            if asyncio.iscoroutinefunction(callback):
                await callback(result)
            else:
                callback(result)

            return True

        return False

    def get_subscription_count(self) -> int:
        """Get number of active subscriptions"""
        return len(self._subscriptions)

    def clear_subscriptions(self) -> None:
        """Clear all active subscriptions (called on disconnect).

        Note: This only clears the active subscription IDs, not the registry.
        The registry is preserved for restoration after reconnection.
        """
        self._subscriptions.clear()

    def clear_registry(self) -> None:
        """Clear the subscription registry completely.

        Call this when you want to stop all subscriptions permanently.
        """
        self._subscriptions.clear()
        self._subscription_registry.clear()

    def get_registry_count(self) -> int:
        """Get number of subscriptions in the registry (for restoration)."""
        return len(self._subscription_registry)

    async def restore_subscriptions(self) -> int:
        """
        Restore all subscriptions after a reconnection.

        This re-subscribes to all previously registered subscriptions
        using the stored callbacks and parameters.

        Returns:
            Number of subscriptions successfully restored
        """
        if not self._subscription_registry:
            logger.debug("No subscriptions to restore")
            return 0

        restored_count = 0
        failed_subscriptions = []

        # Create a copy of the registry to iterate over
        registry_copy = list(self._subscription_registry)

        # Clear the registry before restoration (will be repopulated by subscribe methods)
        self._subscription_registry.clear()

        for info in registry_copy:
            try:
                if info.subscription_type == SubscriptionType.NEW_HEADS:
                    new_id = await self.subscribe_new_heads(info.callback)
                    logger.info(f"Restored newHeads subscription: {new_id}")
                    restored_count += 1

                elif info.subscription_type == SubscriptionType.LOGS:
                    addresses = info.params.get("addresses", []) if info.params else []
                    new_id = await self.subscribe_logs(addresses, info.callback)
                    logger.info(f"Restored logs subscription: {new_id}")
                    restored_count += 1

                elif info.subscription_type == SubscriptionType.PENDING_TRANSACTIONS:
                    new_id = await self.subscribe_pending_transactions(info.callback)
                    logger.info(f"Restored pending transactions subscription: {new_id}")
                    restored_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to restore {info.subscription_type.value} subscription: {e}"
                )
                # Keep track of failed subscriptions for potential retry
                failed_subscriptions.append(info)

        # Add failed subscriptions back to registry for potential future retry
        self._subscription_registry.extend(failed_subscriptions)

        if restored_count > 0:
            logger.info(f"Successfully restored {restored_count} subscription(s)")
        if failed_subscriptions:
            logger.warning(
                f"Failed to restore {len(failed_subscriptions)} subscription(s)"
            )

        return restored_count
