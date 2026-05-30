"""
JSON-RPC payload construction and result extraction.

Separates payload building and response parsing from the HTTP transport
so that ``RPCClient`` can focus on connection management and retries.
"""

from __future__ import annotations

from ..core.exceptions import RPCError


def build_single_payload(
    request_id: int,
    method: str,
    params: list | dict | None,
) -> dict:
    """Build a single JSON-RPC 2.0 request payload."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or [],
    }


def build_batch_payload(
    requests: list[tuple[str, list | dict | None]],
    base_id: int,
) -> list[dict]:
    """Build a batch JSON-RPC 2.0 payload.

    Args:
        requests: List of ``(method, params)`` tuples.
        base_id: First request ID; subsequent IDs are ``base_id + i``.
    """
    return [
        build_single_payload(base_id + i, method, params)
        for i, (method, params) in enumerate(requests)
    ]


def extract_single_result(data: dict) -> object:
    """Extract *result* from a single JSON-RPC response or raise ``RPCError``."""
    if "error" in data:
        error = data["error"]
        raise RPCError(
            message=error.get("message", "Unknown RPC error"),
            code=error.get("code"),
            data=error.get("data"),
        )
    return data.get("result")


def extract_batch_results(raw: list) -> list:
    """Sort *raw* batch response items by *id* and extract results.

    Raises ``RPCError`` for the first error item encountered.
    """
    raw.sort(key=lambda r: r["id"])
    return [extract_single_result(item) for item in raw]
