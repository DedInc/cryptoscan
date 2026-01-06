"""
Security utilities for CryptoScan

Provides URL validation and address masking for secure logging.
"""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Optional


# Valid URL schemes for RPC endpoints
VALID_RPC_SCHEMES = frozenset({"http", "https", "ws", "wss"})

# Minimum address length for masking (to avoid masking very short strings)
MIN_ADDRESS_LENGTH_FOR_MASKING = 12


def validate_rpc_url(url: str) -> bool:
    """Validate that an RPC URL is safe and well-formed.

    Args:
        url: The RPC URL to validate

    Returns:
        True if the URL is valid and uses an allowed scheme,
        False otherwise

    Examples:
        >>> validate_rpc_url("https://ethereum-rpc.publicnode.com")
        True
        >>> validate_rpc_url("wss://ethereum-rpc.publicnode.com")
        True
        >>> validate_rpc_url("file:///etc/passwd")
        False
        >>> validate_rpc_url("javascript:alert(1)")
        False
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        # Check scheme is allowed
        if parsed.scheme.lower() not in VALID_RPC_SCHEMES:
            return False

        # Must have a netloc (host)
        if not parsed.netloc:
            return False

        # Basic sanity check - no obvious injection attempts
        if any(char in url for char in ["<", ">", '"', "'"]):
            return False

        return True
    except Exception:
        return False


def validate_ws_url(url: str) -> bool:
    """Validate that a WebSocket URL is safe and well-formed.

    Args:
        url: The WebSocket URL to validate

    Returns:
        True if the URL is valid and uses ws:// or wss://,
        False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in {"ws", "wss"} and bool(parsed.netloc)
    except Exception:
        return False


def mask_address(address: str, prefix_length: int = 8, suffix_length: int = 6) -> str:
    """Mask a wallet address for safe logging.

    Preserves the beginning and end of the address while masking the middle,
    making it suitable for logging without exposing the full address.

    Args:
        address: The wallet address to mask
        prefix_length: Number of characters to show at the start (default: 8)
        suffix_length: Number of characters to show at the end (default: 6)

    Returns:
        Masked address string (e.g., "0x1234ab...7890ef")

    Examples:
        >>> mask_address("0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23")
        '0x742d35...f8fE23'
        >>> mask_address("short")
        'short'
    """
    if not address or not isinstance(address, str):
        return address or ""

    # Don't mask if address is too short
    if len(address) < MIN_ADDRESS_LENGTH_FOR_MASKING:
        return address

    # Don't mask if we'd show more than we hide
    if prefix_length + suffix_length > len(address):
        return address

    return f"{address[:prefix_length]}...{address[-suffix_length:]}"


def mask_transaction_id(tx_id: str, visible_length: int = 16) -> str:
    """Mask a transaction ID for safe logging.

    Shows only the first N characters followed by ellipsis.

    Args:
        tx_id: The transaction ID to mask
        visible_length: Number of characters to show (default: 16)

    Returns:
        Masked transaction ID (e.g., "0x1234567890abcdef...")
    """
    if not tx_id or not isinstance(tx_id, str):
        return tx_id or ""

    if len(tx_id) <= visible_length:
        return tx_id

    return f"{tx_id[:visible_length]}..."


def sanitize_log_data(data: dict, keys_to_mask: Optional[set] = None) -> dict:
    """Sanitize a dictionary for safe logging by masking sensitive values.

    Args:
        data: Dictionary containing data to log
        keys_to_mask: Set of keys whose values should be masked
                     (default: common sensitive keys)

    Returns:
        New dictionary with sensitive values masked
    """
    if keys_to_mask is None:
        keys_to_mask = {
            "address",
            "wallet_address",
            "from_address",
            "to_address",
            "transaction_id",
            "tx_id",
            "hash",
            "private_key",
            "secret",
            "api_key",
            "password",
            "token",
        }

    result = {}
    for key, value in data.items():
        if key.lower() in keys_to_mask:
            if isinstance(value, str):
                if "address" in key.lower():
                    result[key] = mask_address(value)
                elif "transaction" in key.lower() or key.lower() in {"hash", "tx_id"}:
                    result[key] = mask_transaction_id(value)
                else:
                    result[key] = "***MASKED***"
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = sanitize_log_data(value, keys_to_mask)
        else:
            result[key] = value

    return result
