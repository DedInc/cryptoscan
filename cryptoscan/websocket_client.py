"""
WebSocket client for real-time blockchain monitoring

Refactored version using SOLID principles with modular components.
This maintains backward compatibility while providing a cleaner architecture.
"""

# Import the new refactored WebSocket client
from .websocket import WebSocketClient

# Re-export for backward compatibility
__all__ = ['WebSocketClient']
