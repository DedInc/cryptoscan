"""
WebSocket message processing

Handles incoming message parsing, routing, and error handling
following single responsibility principle.
"""

import asyncio
import json
import logging

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from .connection_manager import WebSocketConnectionManager
from .subscription_manager import WebSocketSubscriptionManager


logger = logging.getLogger(__name__)

# Maximum WebSocket message size (1MB) to prevent memory exhaustion
MAX_MESSAGE_SIZE = 1 * 1024 * 1024


class WebSocketMessageProcessor:
    """Processes incoming WebSocket messages"""

    def __init__(
        self,
        connection_manager: WebSocketConnectionManager,
        subscription_manager: WebSocketSubscriptionManager,
    ):
        self.connection = connection_manager
        self.subscriptions = subscription_manager

    async def listen(self) -> None:
        """
        Listen for subscription messages and process them
        This is the main message processing loop
        """
        self.connection.set_running(True)

        try:
            while self.connection.is_running() and self.connection.is_connected():
                try:
                    # Receive message with timeout
                    timeout = self.connection.config.ws_ping_timeout + 5
                    message = await self.connection.receive_message(timeout=timeout)

                    # Process the message
                    await self._process_message(message)

                except asyncio.TimeoutError:
                    # Normal timeout, check if still running
                    continue

                except Exception as e:
                    # Handle WebSocket errors
                    if await self._handle_connection_error(e):
                        continue  # Reconnection successful, continue listening
                    else:
                        break  # Failed to reconnect, exit loop

        finally:
            self.connection.set_running(False)

    async def _process_message(self, message: str) -> None:
        """Process a single incoming message"""
        # Validate message size to prevent memory exhaustion
        if len(message) > MAX_MESSAGE_SIZE:
            logger.warning(
                f"WebSocket message too large ({len(message)} bytes), ignoring"
            )
            return

        try:
            data = json.loads(message)

            # Try to handle as subscription message
            if await self.subscriptions.handle_subscription_message(data):
                return  # Successfully handled

            # Handle other message types if needed
            logger.debug(f"Unhandled WebSocket message: {data}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message as JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    async def _handle_connection_error(self, error: Exception) -> bool:
        """
        Handle connection errors and attempt reconnection

        Args:
            error: The exception that occurred

        Returns:
            True if reconnection was successful, False otherwise
        """
        if WEBSOCKETS_AVAILABLE and isinstance(
            error, websockets.exceptions.ConnectionClosed
        ):
            logger.warning("WebSocket connection closed, attempting reconnect...")

            # Clear active subscriptions (server-side subscription IDs are now invalid)
            # Note: The subscription registry is preserved for restoration
            self.subscriptions.clear_subscriptions()

            # Attempt reconnection
            if await self.connection.reconnect():
                logger.info("Reconnected successfully, restoring subscriptions...")

                # Restore all subscriptions from the registry
                try:
                    restored_count = await self.subscriptions.restore_subscriptions()
                    if restored_count > 0:
                        logger.info(
                            f"Restored {restored_count} subscription(s) after reconnection"
                        )
                    else:
                        logger.debug("No subscriptions to restore")
                except Exception as restore_error:
                    logger.error(f"Error restoring subscriptions: {restore_error}")
                    # Continue anyway - partial restoration is better than none

                return True
            else:
                logger.error("Failed to reconnect WebSocket")
                return False

        else:
            logger.error(f"WebSocket error: {error}")
            await asyncio.sleep(0.5)  # Brief pause before continuing
            return True  # Continue trying

    def stop(self) -> None:
        """Stop the message processing loop"""
        self.connection.set_running(False)
