"""
Factory functions for creating monitors and providers
"""

from decimal import Decimal
from typing import Optional, Union

from .config import UserConfig
from .exceptions import ValidationError
from .monitoring import PaymentMonitor
from .universal_provider import UniversalProvider
from .networks import get_network, list_networks as get_network_list, NetworkConfig


def _should_use_realtime(network_config: NetworkConfig, custom_rpc_url: Optional[str] = None) -> bool:
    """Detect if real-time monitoring should be used based on WebSocket availability"""
    # Check custom RPC URL first
    if custom_rpc_url and custom_rpc_url.startswith('wss://'):
        return True
    
    # Check if network has WebSocket configured
    if network_config.ws_url is not None:
        return True
    
    # No WebSocket available, use polling
    return False


def create_monitor(
    network: str | NetworkConfig,  # Network name OR NetworkConfig object
    wallet_address: str,
    expected_amount: Union[str, Decimal],
    poll_interval: float = 15.0,
    max_transactions: int = 10,
    auto_stop: bool = False,
    rpc_url: Optional[str] = None,
    ws_url: Optional[str] = None,  # Optional WebSocket URL
    monitor_id: Optional[str] = None,
    user_config: Optional[UserConfig] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    realtime: Optional[bool] = None,  # Auto-detect: None = smart detection
    min_confirmations: int = 1,  # Minimum confirmations required
    **kwargs
) -> PaymentMonitor:
    """Create a payment monitor for any blockchain network
    
    Supports any blockchain (EVM, Solana, Bitcoin, etc.) through:
    1. Predefined network names (e.g., "ethereum", "solana")
    2. Custom NetworkConfig objects for any network
    3. Custom RPC/WebSocket URLs
    
    Auto-detects monitoring mode:
    - WebSocket (real-time) if ws_url provided or rpc_url starts with wss://
    - Polling mode otherwise
    - Can be forced with realtime parameter
    
    Args:
        network: Network name (str) OR NetworkConfig object for custom networks
        wallet_address: Wallet address to monitor
        expected_amount: Expected payment amount (exact match)
        poll_interval: Seconds between checks for polling mode (default: 15.0)
        max_transactions: Max transactions to check per poll (default: 10)
        auto_stop: Stop monitoring after finding payment (default: False)
        rpc_url: Custom RPC URL (optional, overrides network config)
        ws_url: Custom WebSocket URL (optional, enables real-time)
        monitor_id: Optional monitor identifier
        user_config: User configuration (optional)
        timeout: Request timeout override
        max_retries: Max retries override
        realtime: Auto-detect (None), force real-time (True), or force polling (False)
        min_confirmations: Minimum confirmations required (default: 1)
        **kwargs: Additional configuration parameters
    
    Returns:
        PaymentMonitor instance
    
    Raises:
        ValidationError: If network is not supported or parameters invalid
    
    Examples:
        >>> monitor = create_monitor(
        ...     network="ethereum",
        ...     wallet_address="0x...",
        ...     expected_amount="1.0",
        ...     auto_stop=True
        ... )
        >>> await monitor.start()
        
        >>> # Custom network via NetworkConfig
        >>> from cryptoscan import NetworkConfig
        >>> custom_net = NetworkConfig(
        ...     name="mychain",
        ...     symbol="MCH",
        ...     rpc_url="https://rpc.mychain.com",
        ...     chain_type="evm",
        ...     decimals=18
        ... )
        >>> monitor = create_monitor(
        ...     network=custom_net,
        ...     wallet_address="0x...",
        ...     expected_amount="1.0"
        ... )
    """
    # Get or create network configuration
    if isinstance(network, NetworkConfig):
        # User provided NetworkConfig directly
        network_config = network
    elif isinstance(network, str):
        # Try to get from registry
        network_config = get_network(network)
        if not network_config:
            # Not in registry - that's OK! User can still provide rpc_url
            if not rpc_url:
                supported = ", ".join(get_network_list())
                raise ValidationError(
                    f"Network '{network}' not in registry. "
                    f"Either add it to NETWORKS or provide rpc_url parameter.\n"
                    f"Registered networks: {supported}"
                )
            # Create minimal config for custom network
            network_config = NetworkConfig(
                name=network,
                symbol="",
                rpc_url=rpc_url,
                ws_url=ws_url,
                chain_type="evm"  # Default assumption
            )
    else:
        raise ValidationError(f"Invalid network parameter type: {type(network)}")
    
    # Override network config with custom URLs if provided
    if rpc_url or ws_url:
        # User provided custom URLs - override config
        from dataclasses import replace
        network_config = replace(
            network_config,
            rpc_url=rpc_url or network_config.rpc_url,
            ws_url=ws_url if ws_url is not None else network_config.ws_url
        )
    
    # Create or configure user config
    if user_config is None:
        user_config = UserConfig()
    
    # Apply overrides
    if timeout is not None:
        user_config.timeout = timeout
    if max_retries is not None:
        user_config.max_retries = max_retries
    
    # Create universal provider
    provider = UniversalProvider(
        network=network_config,
        rpc_url=None,  # Already in network_config
        user_config=user_config
    )
    
    # Validate address format
    if not network_config.validate_address(wallet_address):
        raise ValidationError(
            f"Invalid {network_config.name} address format: {wallet_address}"
        )
    
    # Auto-detect real-time monitoring mode
    if realtime is None:
        # Auto-detect based on WebSocket availability
        realtime = _should_use_realtime(network_config, rpc_url)
    
    # Create and return monitor
    return PaymentMonitor(
        provider=provider,
        wallet_address=wallet_address,
        expected_amount=expected_amount,
        poll_interval=poll_interval,
        max_transactions=max_transactions,
        auto_stop=auto_stop,
        monitor_id=monitor_id,
        user_config=user_config,
        realtime=realtime,
        min_confirmations=min_confirmations
    )


def get_supported_networks() -> list[str]:
    """
    Get list of all supported network names
    
    Returns:
        List of all available network identifiers (including aliases)
    """
    return get_network_list()


def get_provider(
    network: str,
    rpc_url: Optional[str] = None,
    user_config: Optional[UserConfig] = None
) -> UniversalProvider:
    """
    Get a universal provider instance for ANY network
    
    Args:
        network: Network name or alias
        rpc_url: Optional custom RPC URL
        user_config: Optional user configuration
    
    Returns:
        UniversalProvider instance that works with any blockchain
    
    Raises:
        ValidationError: If network not supported
    """
    network_config = get_network(network)
    if not network_config:
        supported = ", ".join(get_network_list())
        raise ValidationError(
            f"Unsupported network: '{network}'. "
            f"Supported networks: {supported}"
        )
    
    return UniversalProvider(
        network=network_config,
        rpc_url=rpc_url,
        user_config=user_config
    )
