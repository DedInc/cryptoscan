"""Network configuration system for CryptoScan

NetworkConfig is a flexible dataclass for defining ANY blockchain network.
The NETWORKS dictionary contains common examples, but you can:
1. Pass NetworkConfig objects directly to create_monitor()
2. Pass custom rpc_url parameter for unlisted networks
3. Add your own networks to NETWORKS if desired

No network needs to be "hardcoded" - the system is fully extensible.
"""

import re
from dataclasses import dataclass
from typing import Optional, Pattern


@dataclass
class NetworkConfig:
    """Network configuration for any blockchain"""
    name: str
    symbol: str
    rpc_url: str
    ws_url: Optional[str] = None
    address_pattern: Optional[str] = None
    decimals: int = 18
    aliases: list[str] = None
    chain_type: str = "evm"  # evm, solana, cosmos, substrate, etc.
    
    # Custom API adapter (optional callable for non-standard APIs)
    api_adapter: Optional[str] = None  # Name of adapter: "ton_center", "ton_grid", etc.
    
    # Custom RPC method names (if different from standard)
    get_balance_method: Optional[str] = None
    get_transactions_method: Optional[str] = None
    get_block_method: Optional[str] = None
    
    # Custom API endpoints (for REST APIs)
    rest_api_base: Optional[str] = None
    rest_transactions_path: Optional[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.address_pattern:
            self._compiled_pattern = re.compile(self.address_pattern)
        else:
            self._compiled_pattern = None
    
    def validate_address(self, address: str) -> bool:
        """Validate address format"""
        if not self._compiled_pattern:
            return True
        return bool(self._compiled_pattern.match(address))


# Dynamic network registry - no hardcoded networks!
# Networks are created on-demand using NetworkConfig objects
# This eliminates the need for a hardcoded NETWORKS dictionary

# Registry for user-added networks (optional convenience)
_registered_networks = {}


def get_network(identifier: str) -> Optional[NetworkConfig]:
    """
    Get network config by name or alias from registered networks
    
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
    
    # Direct match
    if identifier in _registered_networks:
        return _registered_networks[identifier]
    
    # Check aliases
    for network in _registered_networks.values():
        if identifier in network.aliases:
            return network
    
    return None


def list_networks() -> list[str]:
    """Get all registered network names and aliases"""
    all_names = set()
    for name, config in _registered_networks.items():
        all_names.add(name)
        all_names.update(config.aliases)
    return sorted(all_names)


def register_network(config: NetworkConfig) -> None:
    """
    Register a network configuration for convenient access
    
    Args:
        config: NetworkConfig to register
        
    Note:
        This is optional - you can always pass NetworkConfig directly
        to create_monitor() without registering it first.
    """
    key = config.name.lower().strip()
    _registered_networks[key] = config


def create_network_config(
    name: str,
    symbol: str,
    rpc_url: str,
    ws_url: Optional[str] = None,
    address_pattern: Optional[str] = None,
    decimals: int = 18,
    aliases: list[str] = None,
    chain_type: str = "evm",
    api_adapter: Optional[str] = None,
    **kwargs
) -> NetworkConfig:
    """
    Factory function to create NetworkConfig objects
    
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
        **kwargs
    )


# Convenience function to register common networks
def register_common_networks() -> None:
    """
    Register some common network configurations for convenience
    
    This is completely optional - users can define their own networks
    or use any RPC endpoint without registration.
    """
    common_networks = [
        NetworkConfig(
            name="ethereum",
            symbol="ETH",
            rpc_url="https://ethereum-rpc.publicnode.com",
            ws_url="wss://ethereum-rpc.publicnode.com",
            address_pattern=r'^0x[a-fA-F0-9]{40}$',
            decimals=18,
            aliases=["eth"],
            chain_type="evm"
        ),
        NetworkConfig(
            name="bsc",
            symbol="BNB",
            rpc_url="https://bsc-rpc.publicnode.com",
            ws_url="wss://bsc-rpc.publicnode.com",
            address_pattern=r'^0x[a-fA-F0-9]{40}$',
            decimals=18,
            aliases=["binance", "bnb"],
            chain_type="evm"
        ),
        NetworkConfig(
            name="polygon",
            symbol="MATIC",
            rpc_url="https://polygon-bor-rpc.publicnode.com",
            ws_url="wss://polygon-bor-rpc.publicnode.com",
            address_pattern=r'^0x[a-fA-F0-9]{40}$',
            decimals=18,
            aliases=["matic"],
            chain_type="evm"
        ),
        NetworkConfig(
            name="solana",
            symbol="SOL",
            rpc_url="https://solana-rpc.publicnode.com",
            ws_url="wss://solana-rpc.publicnode.com",
            address_pattern=r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
            decimals=9,
            aliases=["sol"],
            chain_type="solana"
        ),
        NetworkConfig(
            name="bitcoin",
            symbol="BTC",
            rpc_url="https://bitcoin-rpc.publicnode.com",
            address_pattern=r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$',
            decimals=8,
            aliases=["btc"],
            chain_type="bitcoin"
        ),
        NetworkConfig(
            name="tron",
            symbol="TRX",
            rpc_url="https://tron-rpc.publicnode.com",
            address_pattern=r'^T[1-9A-HJ-NP-Za-km-z]{33}$',
            decimals=6,
            aliases=["trx"],
            chain_type="tron"
        )
    ]
    
    for network in common_networks:
        register_network(network)
