"""
Configuration classes for CryptoScan
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


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
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    ssl_verify: bool = True
    connector_limit: int = 100

    # WebSocket specific
    ws_ping_interval: float = 20.0
    ws_ping_timeout: float = 10.0
    ws_max_reconnect_attempts: int = 5
    ws_reconnect_delay: float = 2.0


def create_user_config(
    proxy_url: Optional[str] = None,
    proxy_auth: Optional[str] = None,
    proxy_headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    ssl_verify: bool = True,
    connector_limit: int = 100,
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
