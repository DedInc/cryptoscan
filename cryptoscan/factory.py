"""
Factory Pattern for CryptoScan

Provides convenient factory methods for creating payment monitors
and network providers for different cryptocurrencies.
"""

from decimal import Decimal
from typing import Optional, Dict, Type
import logging

from .core.base import BaseNetworkProvider, UserConfig
from .core.monitor import PaymentMonitor
from .providers.solana import SolanaProvider
from .providers.ethereum import EthereumProvider
from .providers.ton import TONProvider
from .providers.usdt_tron import USDTTronProvider
from .providers.bitcoin import BitcoinProvider
from .config import CryptoScanConfig, default_config
from .exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for network providers."""
    
    _providers: Dict[str, Type[BaseNetworkProvider]] = {
        "solana": SolanaProvider,
        "sol": SolanaProvider,  # Alias
        "ethereum": EthereumProvider,
        "eth": EthereumProvider,  # Alias
        "bitcoin": BitcoinProvider,
        "btc": BitcoinProvider,  # Alias
        "ton": TONProvider,
        "usdt_tron": USDTTronProvider,
        "usdt": USDTTronProvider,  # Alias
        "trc20": USDTTronProvider,  # Alias
    }
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseNetworkProvider]) -> None:
        """
        Register a new network provider.
        
        Args:
            name: Network name (e.g., 'ethereum', 'bitcoin')
            provider_class: Provider class that inherits from BaseNetworkProvider
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered provider '{name}' -> {provider_class.__name__}")
    
    @classmethod
    def get(cls, name: str) -> Type[BaseNetworkProvider]:
        """
        Get a provider class by name.
        
        Args:
            name: Network name
            
        Returns:
            Provider class
            
        Raises:
            ConfigurationError: If provider is not registered
        """
        provider_class = cls._providers.get(name.lower())
        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ConfigurationError(
                f"Provider '{name}' not found. Available providers: {available}"
            )
        return provider_class
    
    @classmethod
    def list_providers(cls) -> Dict[str, Type[BaseNetworkProvider]]:
        """Get all registered providers."""
        return cls._providers.copy()


class CryptoScanFactory:
    """
    Factory class for creating CryptoScan components.
    
    Provides convenient methods for creating payment monitors
    and network providers with sensible defaults.
    """
    
    def __init__(self, config: Optional[CryptoScanConfig] = None):
        """
        Initialize factory with configuration.
        
        Args:
            config: CryptoScan configuration. Uses default if None.
        """
        self.config = config or default_config
    
    def create_provider(self, network: str,
                       user_config: Optional[UserConfig] = None) -> BaseNetworkProvider:
        """
        Create a network provider for the specified cryptocurrency.

        Args:
            network: Network name (e.g., 'solana', 'ethereum', 'bitcoin')
            user_config: User-configurable settings (proxy, timeouts, etc.).
                        Core network settings (RPC URL, headers) are preserved from defaults.

        Returns:
            Configured network provider instance

        Raises:
            ConfigurationError: If network is not supported
        """
        provider_class = ProviderRegistry.get(network)

        # Get the default network config for this provider
        try:
            base_config = self.config.get_network_config(network.lower())
        except ConfigurationError:
            # Use provider's default config if not found in main config
            base_config = None

        # Apply user configuration if provided
        if user_config is not None and base_config is not None:
            final_config = base_config.apply_user_config(user_config)
        else:
            final_config = base_config

        return provider_class(final_config)
    
    def create_monitor(self,
                      network: str,
                      wallet_address: str,
                      expected_amount: str | Decimal,

                      poll_interval: Optional[float] = None,
                      max_transactions: Optional[int] = None,
                      auto_stop: bool = False,
                      user_config: Optional[UserConfig] = None,
                      monitor_id: Optional[str] = None) -> PaymentMonitor:
        """
        Create a payment monitor for the specified cryptocurrency.

        Args:
            network: Network name (e.g., 'solana', 'ethereum', 'bitcoin')
            wallet_address: Wallet address to monitor
            expected_amount: Expected payment amount

            poll_interval: Seconds between polling cycles
            max_transactions: Maximum transactions to check per poll
            user_config: User-configurable settings (proxy, timeouts, etc.).
                        Core network settings (RPC URL, headers) are preserved from defaults.
            monitor_id: Unique identifier for this monitor

        Returns:
            Configured PaymentMonitor instance

        Raises:
            ConfigurationError: If network is not supported
            ValidationError: If parameters are invalid
        """
        # Create provider
        provider = self.create_provider(network, user_config)

        # Use defaults from config if not specified
        if poll_interval is None:
            poll_interval = self.config.default_poll_interval
        if max_transactions is None:
            max_transactions = self.config.default_max_transactions

        return PaymentMonitor(
            provider=provider,
            wallet_address=wallet_address,
            expected_amount=expected_amount,
            poll_interval=poll_interval,
            max_transactions=max_transactions,
            auto_stop=auto_stop,
            monitor_id=monitor_id
        )
    



# Global factory instance
factory = CryptoScanFactory()


# Main API - Provider-agnostic payment monitoring
def create_monitor(network: str,
                  wallet_address: str,
                  expected_amount: str | Decimal,
                  poll_interval: Optional[float] = None,
                  max_transactions: Optional[int] = None,
                  auto_stop: bool = False,
                  user_config: Optional[UserConfig] = None,
                  **kwargs) -> PaymentMonitor:
    """
    Create a payment monitor for any supported cryptocurrency network.

    This is the main API function that provides a unified interface for monitoring
    payments across different blockchain networks without needing to know the
    specific provider implementation details.

    Args:
        network: Network name (e.g., 'solana', 'ethereum', 'bitcoin', 'dogecoin', 'ton')
        wallet_address: Wallet address to monitor for payments
        expected_amount: Expected payment amount (exact match)
        poll_interval: Seconds between polling cycles (default: 15.0)
        max_transactions: Maximum transactions to check per poll (default: 10)
        auto_stop: Whether to automatically stop after finding payment (default: False)
        user_config: User-configurable settings (proxy, timeouts, etc.).
                    Core network settings (RPC URL, headers) are preserved from defaults.
        **kwargs: Additional user configuration options (timeout, max_retries, etc.)

    Returns:
        Configured PaymentMonitor instance ready to start monitoring

    Example:
        # Solana payment monitoring with proxy
        from cryptoscan import create_monitor, UserConfig, ProxyConfig

        user_cfg = UserConfig(
            proxy_config=ProxyConfig(
                https_proxy="https://proxy.example.com:8080",
                proxy_auth="username:password"
            ),
            timeout=60,
            max_retries=5
        )

        monitor = create_monitor(
            network="solana",
            wallet_address="39eda9Jzabcr1HPkmjt7sZPCznZqngkfXZn1utwE8uwk",
            expected_amount="0.1",
            poll_interval=10.0,
            user_config=user_cfg
        )

        # Simple monitoring
        monitor = create_monitor(
            network="ethereum",
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            expected_amount="0.05"
        )
    """
    # Create user config from kwargs if not provided
    if user_config is None and kwargs:
        from .core.base import ProxyConfig

        # Extract proxy-related kwargs
        proxy_kwargs = {}
        if 'proxy_url' in kwargs or 'https_proxy' in kwargs:
            proxy_kwargs['https_proxy'] = kwargs.pop('proxy_url', kwargs.pop('https_proxy', None))
        if 'http_proxy' in kwargs:
            proxy_kwargs['http_proxy'] = kwargs.pop('http_proxy')
        if 'proxy_auth' in kwargs:
            proxy_kwargs['proxy_auth'] = kwargs.pop('proxy_auth')
        if 'proxy_headers' in kwargs:
            proxy_kwargs['proxy_headers'] = kwargs.pop('proxy_headers')

        proxy_config = ProxyConfig(**proxy_kwargs) if proxy_kwargs else None

        # Create user config with remaining kwargs
        user_config = UserConfig(
            proxy_config=proxy_config,
            **kwargs
        )

    return factory.create_monitor(
        network=network,
        wallet_address=wallet_address,
        expected_amount=expected_amount,
        poll_interval=poll_interval,
        max_transactions=max_transactions,
        user_config=user_config,
        auto_stop=auto_stop
    )





def register_provider(name: str, provider_class: Type[BaseNetworkProvider]) -> None:
    """
    Register a new network provider.
    
    Args:
        name: Network name
        provider_class: Provider class
    """
    ProviderRegistry.register(name, provider_class)


def list_supported_networks() -> Dict[str, Type[BaseNetworkProvider]]:
    """Get all supported networks and their provider classes."""
    return ProviderRegistry.list_providers()
