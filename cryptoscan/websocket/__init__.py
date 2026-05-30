"""
WebSocket module for CryptoScan

Provides a clean, modular WebSocket client system following SOLID principles:
- ConnectionManager: Handles connection lifecycle
- SubscriptionManager: Manages subscriptions and callbacks
- MessageProcessor: Processes incoming messages
- WebSocketClient: Facade that combines all components
"""

from .client import WebSocketClient
from .connection_manager import WebSocketConnectionManager
from .message_processor import WebSocketMessageProcessor
from .subscription_manager import WebSocketSubscriptionManager

__all__ = [
    "WebSocketConnectionManager",
    "WebSocketSubscriptionManager",
    "WebSocketMessageProcessor",
    "WebSocketClient",
]
