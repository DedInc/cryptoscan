"""
WebSocket subscription management

Handles subscription lifecycle, request ID management, and callback organization
following single responsibility principle.
"""

import asyncio
import json
import logging
from typing import Dict, Callable, Any, Optional

from .connection_manager import WebSocketConnectionManager
from ..exceptions import ConnectionError as CSConnectionError


logger = logging.getLogger(__name__)


class WebSocketSubscriptionManager:
    """Manages WebSocket subscriptions and callbacks"""
    
    def __init__(self, connection_manager: WebSocketConnectionManager):
        self.connection = connection_manager
        self._subscriptions: Dict[str, Callable] = {}
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
            "params": ["newHeads"]
        }
        
        await self.connection.send_message(json.dumps(subscribe_msg))
        response = json.loads(await self.connection.receive_message())
        
        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)
        
        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback
        
        logger.info(f"Subscribed to newHeads with ID: {subscription_id}")
        return subscription_id
    
    async def subscribe_logs(self, addresses: list[str], callback: Callable[[dict], Any]) -> str:
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
            "params": ["logs", {"address": addresses}]
        }
        
        await self.connection.send_message(json.dumps(subscribe_msg))
        response = json.loads(await self.connection.receive_message())
        
        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)
        
        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback
        
        logger.info(f"Subscribed to logs for {len(addresses)} addresses")
        return subscription_id
    
    async def subscribe_pending_transactions(self, callback: Callable[[str], Any]) -> str:
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
            "params": ["newPendingTransactions"]
        }
        
        await self.connection.send_message(json.dumps(subscribe_msg))
        response = json.loads(await self.connection.receive_message())
        
        if "error" in response:
            raise CSConnectionError(f"Subscription failed: {response['error']}", None)
        
        subscription_id = response.get("result")
        self._subscriptions[subscription_id] = callback
        
        logger.info(f"Subscribed to pending transactions")
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
            "params": [subscription_id]
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
        
        if subscription_id in self._subscriptions:
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
        """Clear all subscriptions (usually called on disconnect)"""
        self._subscriptions.clear()