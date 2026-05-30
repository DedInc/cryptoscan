"""
WebSocket JSON-RPC message builders for subscription operations.

Each function returns a JSON-serializable ``dict`` ready for ``json.dumps``.
"""

from __future__ import annotations


def build_subscribe_new_heads(request_id: int) -> dict:
    """Build an ``eth_subscribe`` message for *newHeads*."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "eth_subscribe",
        "params": ["newHeads"],
    }


def build_subscribe_logs(request_id: int, addresses: list[str]) -> dict:
    """Build an ``eth_subscribe`` message for *logs* filtered by *addresses*."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "eth_subscribe",
        "params": ["logs", {"address": addresses}],
    }


def build_subscribe_pending_transactions(request_id: int) -> dict:
    """Build an ``eth_subscribe`` message for *newPendingTransactions*."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "eth_subscribe",
        "params": ["newPendingTransactions"],
    }


def build_unsubscribe(request_id: int, subscription_id: str) -> dict:
    """Build an ``eth_unsubscribe`` message for the given *subscription_id*."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "eth_unsubscribe",
        "params": [subscription_id],
    }
