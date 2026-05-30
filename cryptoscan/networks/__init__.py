"""Network configuration system for CryptoScan.

NetworkConfig is a flexible dataclass for defining ANY blockchain network.
The NETWORKS dictionary contains common examples, but you can:
1. Pass NetworkConfig objects directly to create_monitor()
2. Pass custom rpc_url parameter for unlisted networks
3. Add your own networks to NETWORKS if desired

No network needs to be "hardcoded" - the system is fully extensible.
"""

from __future__ import annotations

__all__ = [
    "NetworkConfig",
    "get_network",
    "list_networks",
    "register_network",
    "create_network_config",
    "register_common_networks",
]

import re
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NetworkConfig:
    """Network configuration for any blockchain."""

    name: str
    symbol: str
    rpc_url: str
    ws_url: str | None = None
    address_pattern: str | None = None
    decimals: int = 18
    aliases: list[str] = field(default_factory=list)
    chain_type: str = "evm"

    api_adapter: str | None = None

    get_balance_method: str | None = None
    get_transactions_method: str | None = None
    get_block_method: str | None = None

    rest_api_base: str | None = None
    rest_transactions_path: str | None = None

    def __post_init__(self) -> None:
        """Initialize computed fields after dataclass creation."""
        if self.address_pattern:
            self._compiled_pattern = re.compile(self.address_pattern)
        else:
            self._compiled_pattern = None

    def validate_address(self, address: str) -> bool:
        """Validate address format against the network's address pattern.

        Args:
            address: The wallet address to validate

        Returns:
            True if address matches the pattern or no pattern is defined,
            False if address doesn't match the expected format
        """
        if not self._compiled_pattern:
            return True
        return bool(self._compiled_pattern.match(address))


_registered_networks = {}
_networks_lock = threading.Lock()


def get_network(identifier: str) -> NetworkConfig | None:
    """Get network config by name or alias from registered networks.

    Args:
        identifier: Network name or alias

    Returns:
        NetworkConfig or None if not registered

    Note:
        This only returns explicitly registered networks.
        For maximum flexibility, pass NetworkConfig objects directly
        to create_monitor() or provide rpc_url parameter.
    """
    identifier = identifier.lower().strip()

    with _networks_lock:
        if identifier in _registered_networks:
            return _registered_networks[identifier]

        for network in _registered_networks.values():
            if identifier in network.aliases:
                return network

    return None


def list_networks() -> list[str]:
    """Get all registered network names and aliases."""
    with _networks_lock:
        all_names = set()
        for name, config in _registered_networks.items():
            all_names.add(name)
            all_names.update(config.aliases)
        return sorted(all_names)


def register_network(config: NetworkConfig) -> None:
    """Register a network configuration for convenient access.

    Args:
        config: NetworkConfig to register

    Note:
        This is optional - you can always pass NetworkConfig directly
        to create_monitor() without registering it first.
    """
    key = config.name.lower().strip()
    with _networks_lock:
        _registered_networks[key] = config


def create_network_config(
    name: str,
    symbol: str,
    rpc_url: str,
    ws_url: str | None = None,
    address_pattern: str | None = None,
    decimals: int = 18,
    aliases: list[str] = None,
    chain_type: str = "evm",
    api_adapter: str | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> NetworkConfig:
    """Factory function to create NetworkConfig objects.

    This is a convenience function for creating network configurations.
    All parameters are passed directly to NetworkConfig constructor.

    Returns:
        NetworkConfig instance
    """
    return NetworkConfig(
        name=name,
        symbol=symbol,
        rpc_url=rpc_url,
        ws_url=ws_url,
        address_pattern=address_pattern,
        decimals=decimals,
        aliases=aliases or [],
        chain_type=chain_type,
        api_adapter=api_adapter,
        **kwargs,
    )


from .defaults import register_common_networks  # noqa: E402,F401
