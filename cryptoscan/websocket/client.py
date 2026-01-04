"""
Refactored WebSocket client using SOLID principles

This is the main facade that combines:
- WebSocketConnectionManager: Connection lifecycle
- WebSocketSubscriptionManager: Subscription management
- WebSocketMessageProcessor: Message processing

Much cleaner and more maintainable than the original 260+ line monolithic class.
"""

from typing import Optional, Callable, Any

from .connection_manager import WebSocketConnectionManager
from .subscription_manager import WebSocketSubscriptionManager
from .message_processor import WebSocketMessageProcessor
from ..config import UserConfig


class WebSocketClient:
    """
    Modern WebSocket client for real-time blockchain monitoring

    This refactored version follows SOLID principles:
    - Single Responsibility: Each component has one job
    - Open/Closed: Easy to extend without modifying existing code
    - Liskov Substitution: Components are interchangeable
    - Interface Segregation: Clean, focused interfaces
    - Dependency Inversion: Depends on abstractions, not concretions
    """

    def __init__(self, ws_url: str, user_config: Optional[UserConfig] = None):
        self.ws_url = ws_url
        self.config = user_config or UserConfig()

        # Create components following dependency injection
        self._connection_manager = WebSocketConnectionManager(ws_url, self.config)
        self._subscription_manager = WebSocketSubscriptionManager(
            self._connection_manager
        )
        self._message_processor = WebSocketMessageProcessor(
            self._connection_manager, self._subscription_manager
        )

    async def connect(self) -> None:
        """Connect to WebSocket endpoint"""
        await self._connection_manager.connect()

    async def close(self) -> None:
        """Close WebSocket connection"""
        self._message_processor.stop()
        await self._connection_manager.close()

    async def subscribe_new_heads(self, callback: Callable[[dict], Any]) -> str:
        """
        Subscribe to new block headers (EVM chains)

        Args:
            callback: Async function to call with each new block header

        Returns:
            Subscription ID
        """
        return await self._subscription_manager.subscribe_new_heads(callback)

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
        return await self._subscription_manager.subscribe_logs(addresses, callback)

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
        return await self._subscription_manager.subscribe_pending_transactions(callback)

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a subscription"""
        await self._subscription_manager.unsubscribe(subscription_id)

    async def listen(self) -> None:
        """
        Listen for subscription messages
        Call this in a background task to receive real-time updates
        """
        await self._message_processor.listen()

    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._connection_manager.is_connected()

    def get_subscription_count(self) -> int:
        """Get number of active subscriptions"""
        return self._subscription_manager.get_subscription_count()

    def __repr__(self) -> str:
        return (
            f"WebSocketClient("
            f"url={self.ws_url}, "
            f"connected={self._connection_manager.is_connected()}, "
            f"subscriptions={self._subscription_manager.get_subscription_count()})"
        )
