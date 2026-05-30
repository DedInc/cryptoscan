"""Address/transaction masking and log sanitization utilities for CryptoScan."""

from __future__ import annotations

__all__ = [
    "MIN_ADDRESS_LENGTH_FOR_MASKING",
    "mask_address",
    "mask_transaction_id",
    "mask_url",
    "sanitize_log_data",
]

from urllib.parse import urlparse

MIN_ADDRESS_LENGTH_FOR_MASKING = 12


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

    if len(address) < MIN_ADDRESS_LENGTH_FOR_MASKING:
        return address

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


def mask_url(url: str) -> str:
    """Mask a URL for safe logging.

    Hides query params and path segments that may contain secrets.

    Examples:
        >>> mask_url("wss://eth-mainnet.g.alchemy.com/v2/abc123apikey")
        'wss://eth-mainnet.g.alchemy.com/v2/***MASKED***'
        >>> mask_url("https://rpc.example.com")
        'https://rpc.example.com'
    """
    if not url or not isinstance(url, str):
        return url or ""
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return "***INVALID_URL***"
        path = parsed.path
        if path and path != "/":
            parts = path.rstrip("/").split("/")
            if len(parts) > 2:
                path = "/".join(parts[:2]) + "/***MASKED***"
        masked = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            masked += "?***MASKED***"
        return masked
    except Exception:
        return "***URL_PARSE_ERROR***"


def sanitize_log_data(data: dict, keys_to_mask: set | None = None) -> dict:
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
