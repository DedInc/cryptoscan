"""
WebSocket connection management

Handles the connection lifecycle, reconnection logic, and basic message I/O
following single responsibility principle.
"""

import asyncio
import logging
from typing import Optional, Callable, Any

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from ..config import UserConfig
from ..exceptions import ConnectionError as CSConnectionError


logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connection lifecycle and basic I/O"""
    
    def __init__(
        self,
        ws_url: str,
        config: UserConfig
    ):
        self.ws_url = ws_url
        self.config = config
        
        self._ws = None
        self._connected = False
        self._running = False
        
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets library not available, WebSocket features disabled")
    
    async def connect(self) -> None:
        """Establish WebSocket connection"""
        if not WEBSOCKETS_AVAILABLE:
            raise CSConnectionError(
                "websockets library not installed. Install with: pip install websockets",
                None
            )
        
        try:
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=self.config.ws_ping_interval,
                ping_timeout=self.config.ws_ping_timeout,
                close_timeout=10
            )
            self._connected = True
            logger.info(f"Connected to WebSocket: {self.ws_url}")
        except Exception as e:
            raise CSConnectionError(f"Failed to connect to WebSocket: {str(e)}", e)
    
    async def close(self) -> None:
        """Close WebSocket connection"""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._connected = False
            logger.info("WebSocket connection closed")
    
    async def send_message(self, message: str) -> None:
        """Send message over WebSocket"""
        if not self._connected or not self._ws:
            raise CSConnectionError("WebSocket not connected", None)
        
        await self._ws.send(message)
    
    async def receive_message(self, timeout: Optional[float] = None) -> str:
        """Receive message from WebSocket with optional timeout"""
        if not self._connected or not self._ws:
            raise CSConnectionError("WebSocket not connected", None)
        
        if timeout:
            return await asyncio.wait_for(self._ws.recv(), timeout=timeout)
        else:
            return await self._ws.recv()
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket with exponential backoff"""
        for attempt in range(self.config.ws_max_reconnect_attempts):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{self.config.ws_max_reconnect_attempts}")
                await asyncio.sleep(self.config.ws_reconnect_delay * (attempt + 1))
                await self.connect()
                logger.info("Reconnected successfully")
                return True
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        logger.error("Max reconnection attempts reached")
        return False
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._connected
    
    def set_running(self, running: bool) -> None:
        """Set running state"""
        self._running = running
    
    def is_running(self) -> bool:
        """Check if connection is in running state"""
        return self._running