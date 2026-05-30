"""URL validation utilities for CryptoScan."""

from __future__ import annotations

__all__ = [
    "VALID_RPC_SCHEMES",
    "validate_rpc_url",
    "validate_ws_url",
]

import ipaddress
import socket
from urllib.parse import urlparse

VALID_RPC_SCHEMES = frozenset({"http", "https", "ws", "wss"})


_PRIVATE_NETWORKS = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv6Network("::1/128"),
]


def _is_private_ip(ip: str) -> bool:
    """Return True if *ip* belongs to a private/reserved range (or 0.0.0.0)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr == ipaddress.IPv4Address("0.0.0.0"):
        return True
    return any(addr in network for network in _PRIVATE_NETWORKS)


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

        if parsed.scheme.lower() not in VALID_RPC_SCHEMES:
            return False

        if not parsed.netloc:
            return False

        if any(char in url for char in ["<", ">", '"', "'"]):
            return False

        host = parsed.hostname or ""
        if not host:
            return False

        try:
            for _family, _, _, _, sockaddr in socket.getaddrinfo(host, None):
                if _is_private_ip(sockaddr[0]):
                    return False
        except (socket.gaierror, OSError):
            pass

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
