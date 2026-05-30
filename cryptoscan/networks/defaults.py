"""Default network configurations for CryptoScan."""

from __future__ import annotations

from . import NetworkConfig, register_network

__all__ = ["register_common_networks"]


def register_common_networks() -> None:
    """Register some common network configurations for convenience.

    This is completely optional - users can define their own networks
    or use any RPC endpoint without registration.
    """
    common_networks = [
        NetworkConfig(
            name="ethereum",
            symbol="ETH",
            rpc_url="https://ethereum-rpc.publicnode.com",
            ws_url="wss://ethereum-rpc.publicnode.com",
            address_pattern=r"^0x[a-fA-F0-9]{40}$",
            decimals=18,
            aliases=["eth"],
            chain_type="evm",
        ),
        NetworkConfig(
            name="bsc",
            symbol="BNB",
            rpc_url="https://bsc-rpc.publicnode.com",
            ws_url="wss://bsc-rpc.publicnode.com",
            address_pattern=r"^0x[a-fA-F0-9]{40}$",
            decimals=18,
            aliases=["binance", "bnb"],
            chain_type="evm",
        ),
        NetworkConfig(
            name="polygon",
            symbol="MATIC",
            rpc_url="https://polygon-bor-rpc.publicnode.com",
            ws_url="wss://polygon-bor-rpc.publicnode.com",
            address_pattern=r"^0x[a-fA-F0-9]{40}$",
            decimals=18,
            aliases=["matic"],
            chain_type="evm",
        ),
        NetworkConfig(
            name="solana",
            symbol="SOL",
            rpc_url="https://solana-rpc.publicnode.com",
            ws_url="wss://solana-rpc.publicnode.com",
            address_pattern=r"^[1-9A-HJ-NP-Za-km-z]{32,44}$",
            decimals=9,
            aliases=["sol"],
            chain_type="solana",
        ),
        NetworkConfig(
            name="bitcoin",
            symbol="BTC",
            rpc_url="https://bitcoin-rpc.publicnode.com",
            address_pattern=r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$",
            decimals=8,
            aliases=["btc"],
            chain_type="bitcoin",
        ),
        NetworkConfig(
            name="tron",
            symbol="TRX",
            rpc_url="https://tron-rpc.publicnode.com",
            address_pattern=r"^T[1-9A-HJ-NP-Za-km-z]{33}$",
            decimals=6,
            aliases=["trx"],
            chain_type="tron",
        ),
    ]

    for network in common_networks:
        register_network(network)
