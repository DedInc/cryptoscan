"""
CryptoScan - Professional Crypto Payment Monitoring Library

A fast, async, and extensible Python library for monitoring cryptocurrency payments
across multiple blockchain networks including Solana, Ethereum, Bitcoin, TON, and etc.
"""

from .core.monitor import PaymentMonitor
from .core.base import BaseNetworkProvider, PaymentInfo, PaymentStatus, NetworkConfig, ProxyConfig, UserConfig
from .providers.solana import SolanaProvider
from .providers.ethereum import EthereumProvider
from .providers.ton import TONProvider
from .providers.usdt_tron import USDTTronProvider
from .providers.bitcoin import BitcoinProvider
from .config import CryptoScanConfig
from .exceptions import CryptoScanError, PaymentNotFoundError, NetworkError
from .factory import (
    create_monitor,
    register_provider,
    list_supported_networks,
    CryptoScanFactory
)
from .utils import (
    create_user_config,
    load_proxy_list,
    test_proxy_config
)

__version__ = "1.0.0"
__author__ = "CryptoScan Team"
__email__ = "support@cryptoscan.dev"

__all__ = [
    # Core classes
    "PaymentMonitor",
    "BaseNetworkProvider",
    "PaymentInfo",
    "PaymentStatus",

    # Provider classes
    "SolanaProvider",
    "EthereumProvider",
    "TONProvider",
    "USDTTronProvider",
    "BitcoinProvider",

    # Configuration
    "CryptoScanConfig",
    "NetworkConfig",
    "ProxyConfig",
    "UserConfig",

    # Exceptions
    "CryptoScanError",
    "PaymentNotFoundError",
    "NetworkError",

    # Main API - Provider-agnostic
    "create_monitor",

    # Advanced API
    "register_provider",
    "list_supported_networks",
    "CryptoScanFactory",

    # Utilities
    "create_user_config",
    "load_proxy_list",
    "test_proxy_config",
]
