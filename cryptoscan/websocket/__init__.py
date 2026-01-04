"""
WebSocket module for CryptoScan

Provides a clean, modular WebSocket client system following SOLID principles:
- ConnectionManager: Handles connection lifecycle
- SubscriptionManager: Manages subscriptions and callbacks
- MessageProcessor: Processes incoming messages
- WebSocketClient: Facade that combines all components
"""

from .connection_manager import WebSocketConnectionManager
from .subscription_manager import WebSocketSubscriptionManager
from .message_processor import WebSocketMessageProcessor
from .client import WebSocketClient

__all__ = [
    "WebSocketConnectionManager",
    "WebSocketSubscriptionManager",
    "WebSocketMessageProcessor",
    "WebSocketClient",
]
