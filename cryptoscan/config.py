"""
Configuration classes for CryptoScan
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


# =============================================================================
# Constants - Centralized configuration values
# =============================================================================

# Block scanning limits
MAX_BLOCKS_TO_SCAN = 100  # Maximum blocks to check (~20 minutes on ETH)
BLOCKS_PER_TX_MULTIPLIER = 5  # Multiplier for limit to determine blocks to check

# WebSocket defaults
DEFAULT_WS_CLOSE_TIMEOUT = 10  # Seconds to wait for WebSocket close
DEFAULT_WS_PING_INTERVAL = 20.0  # Seconds between WebSocket pings
DEFAULT_WS_PING_TIMEOUT = 10.0  # Seconds to wait for ping response
DEFAULT_WS_MAX_RECONNECT_ATTEMPTS = 5  # Max reconnection attempts
DEFAULT_WS_RECONNECT_DELAY = 2.0  # Seconds between reconnection attempts

# HTTP/RPC defaults
DEFAULT_HTTP_TIMEOUT = 30.0  # Seconds for HTTP request timeout
DEFAULT_MAX_RETRIES = 3  # Maximum retry attempts
DEFAULT_RETRY_DELAY = 1.0  # Seconds between retries
DEFAULT_CONNECTOR_LIMIT = 100  # Maximum concurrent connections

# Adapter defaults
DEFAULT_ADAPTER_TIMEOUT = 30.0  # Seconds for adapter HTTP timeout


@dataclass
class ProxyConfig:
    """Proxy configuration"""

    https_proxy: Optional[str] = None
    http_proxy: Optional[str] = None
    proxy_auth: Optional[str] = None
    proxy_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_url(cls, proxy_url: str, auth: str = None, headers: Dict[str, str] = None):
        """Create ProxyConfig from URL"""
        return cls(
            https_proxy=proxy_url,
            http_proxy=proxy_url,
            proxy_auth=auth,
            proxy_headers=headers or {},
        )


@dataclass
class UserConfig:
    """User configuration for monitors and providers"""

    proxy_config: Optional[ProxyConfig] = None
    timeout: float = DEFAULT_HTTP_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    ssl_verify: bool = True
    connector_limit: int = DEFAULT_CONNECTOR_LIMIT

    # WebSocket specific
    ws_ping_interval: float = DEFAULT_WS_PING_INTERVAL
    ws_ping_timeout: float = DEFAULT_WS_PING_TIMEOUT
    ws_max_reconnect_attempts: int = DEFAULT_WS_MAX_RECONNECT_ATTEMPTS
    ws_reconnect_delay: float = DEFAULT_WS_RECONNECT_DELAY

    # Block scanning configuration (overrides module-level constants)
    max_blocks_to_scan: int = MAX_BLOCKS_TO_SCAN
    blocks_per_tx_multiplier: int = BLOCKS_PER_TX_MULTIPLIER


def create_user_config(
    proxy_url: Optional[str] = None,
    proxy_auth: Optional[str] = None,
    proxy_headers: Optional[Dict[str, str]] = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    ssl_verify: bool = True,
    connector_limit: int = DEFAULT_CONNECTOR_LIMIT,
) -> UserConfig:
    """Factory function to create UserConfig with proxy support"""
    proxy_config = None
    if proxy_url:
        proxy_config = ProxyConfig.from_url(proxy_url, proxy_auth, proxy_headers)

    return UserConfig(
        proxy_config=proxy_config,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        ssl_verify=ssl_verify,
        connector_limit=connector_limit,
    )
