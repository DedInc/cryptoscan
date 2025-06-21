"""
Base Classes and Interfaces for CryptoScan

Defines the core abstractions that all network providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx


class PaymentStatus(Enum):
    """Status of a payment transaction."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PaymentInfo:
    """Information about a detected payment."""
    
    transaction_id: str
    wallet_address: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    timestamp: datetime
    block_height: Optional[int] = None
    confirmations: Optional[int] = None
    fee: Optional[Decimal] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Ensure amount is a Decimal for precise calculations."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        if self.fee is not None and not isinstance(self.fee, Decimal):
            self.fee = Decimal(str(self.fee))


@dataclass
class ProxyConfig:
    """Proxy configuration for network requests."""

    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    proxy_auth: Optional[str] = None
    proxy_headers: Optional[Dict[str, str]] = None

    def get_proxy_url(self, scheme: str = "https") -> Optional[str]:
        """Get proxy URL for the given scheme."""
        if scheme.lower() == "https" and self.https_proxy:
            return self.https_proxy
        elif scheme.lower() == "http" and self.http_proxy:
            return self.http_proxy
        return self.https_proxy or self.http_proxy

    def get_proxy_auth(self) -> Optional[str]:
        """Get proxy authentication string if configured."""
        return self.proxy_auth


@dataclass
class UserConfig:
    """User-configurable settings that can be safely modified without breaking provider functionality."""

    proxy_config: Optional[ProxyConfig] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # SSL settings that users might want to customize
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

    # Connection settings users might want to tune
    connector_limit: int = 100
    connector_limit_per_host: int = 30

    # Cookie and session settings
    cookie_jar: Optional[str] = None  # Path to cookie jar file
    trust_env: bool = True  # Trust environment variables for proxy


@dataclass
class NetworkConfig:
    """Configuration for a specific network provider."""

    rpc_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: Optional[float] = None
    headers: Optional[Dict[str, str]] = None
    proxy_config: Optional[ProxyConfig] = None

    # Advanced connection settings
    connector_limit: int = 100
    connector_limit_per_host: int = 30
    connector_ttl_dns_cache: int = 300
    connector_use_dns_cache: bool = True

    # SSL settings
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

    # Cookie and session settings
    cookie_jar: Optional[str] = None  # Path to cookie jar file
    trust_env: bool = True  # Trust environment variables for proxy

    def apply_user_config(self, user_config: UserConfig) -> 'NetworkConfig':
        """
        Apply user configuration to this network config, preserving critical provider settings.

        Args:
            user_config: User-configurable settings

        Returns:
            New NetworkConfig with user settings applied
        """
        return NetworkConfig(
            # Preserve critical provider-specific settings
            rpc_url=self.rpc_url,
            api_key=self.api_key,
            headers=self.headers,
            rate_limit_per_second=self.rate_limit_per_second,
            connector_ttl_dns_cache=self.connector_ttl_dns_cache,
            connector_use_dns_cache=self.connector_use_dns_cache,

            # Apply user-configurable settings
            proxy_config=user_config.proxy_config,
            timeout=user_config.timeout,
            max_retries=user_config.max_retries,
            retry_delay=user_config.retry_delay,
            ssl_verify=user_config.ssl_verify,
            ssl_cert_path=user_config.ssl_cert_path,
            ssl_key_path=user_config.ssl_key_path,
            connector_limit=user_config.connector_limit,
            connector_limit_per_host=user_config.connector_limit_per_host,
            cookie_jar=user_config.cookie_jar,
            trust_env=user_config.trust_env,
        )

    def get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP requests."""
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CryptoScan/1.0.0'
        }
        if self.headers:
            default_headers.update(self.headers)
        return default_headers

    def get_httpx_kwargs(self) -> Dict[str, Any]:
        """Get httpx client configuration."""
        kwargs = {
            'timeout': self.timeout,
            'headers': self.get_headers(),
            'trust_env': self.trust_env,
            'http2': True,  # Enable HTTP/2 by default
        }

        # SSL configuration
        if not self.ssl_verify:
            kwargs['verify'] = False
        elif self.ssl_cert_path or self.ssl_key_path:
            # For httpx, SSL cert configuration is handled differently
            if self.ssl_cert_path:
                kwargs['cert'] = (self.ssl_cert_path, self.ssl_key_path) if self.ssl_key_path else self.ssl_cert_path

        # Proxy configuration
        if self.proxy_config:
            proxy_url = self.proxy_config.get_proxy_url("https")
            if proxy_url:
                # Add authentication to proxy URL if available
                proxy_auth = self.proxy_config.get_proxy_auth()
                if proxy_auth and '@' not in proxy_url:
                    if proxy_url.startswith('http://'):
                        proxy_url = f"http://{proxy_auth}@{proxy_url[7:]}"
                    elif proxy_url.startswith('https://'):
                        proxy_url = f"https://{proxy_auth}@{proxy_url[8:]}"

                kwargs['proxy'] = proxy_url

        return kwargs


class BaseNetworkProvider(ABC):
    """
    Abstract base class for all cryptocurrency network providers.
    
    Each blockchain implementation (Solana, Ethereum, Bitcoin, etc.) 
    must inherit from this class and implement all abstract methods.
    """
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    @abstractmethod
    def currency_symbol(self) -> str:
        """Return the currency symbol (e.g., 'SOL', 'ETH', 'BTC')."""
        pass
    
    @property
    @abstractmethod
    def network_name(self) -> str:
        """Return the network name (e.g., 'Solana', 'Ethereum', 'Bitcoin')."""
        pass
    
    @property
    @abstractmethod
    def smallest_unit_name(self) -> str:
        """Return the smallest unit name (e.g., 'lamports', 'wei', 'satoshi')."""
        pass
    
    @property
    @abstractmethod
    def units_per_token(self) -> int:
        """Return how many smallest units make up one token."""
        pass
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create an httpx client with full configuration support."""
        if self._client is None or self._client.is_closed:
            # Get httpx configuration from NetworkConfig
            client_kwargs = self.config.get_httpx_kwargs()

            # Create the httpx client
            self._client = httpx.AsyncClient(**client_kwargs)

        return self._client

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with proxy and retry support."""
        client = await self.get_client()

        # Add proxy headers if configured
        if (self.config.proxy_config and
            self.config.proxy_config.proxy_headers):
            headers = kwargs.get('headers', {})
            headers.update(self.config.proxy_config.proxy_headers)
            kwargs['headers'] = headers

        return await client.request(method, url, **kwargs)

    async def close(self):
        """Close the httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def get_recent_transactions(self, wallet_address: str, 
                                    limit: int = 10) -> List[PaymentInfo]:
        """
        Get recent transactions for a wallet address.
        
        Args:
            wallet_address: The wallet address to monitor
            limit: Maximum number of transactions to return
            
        Returns:
            List of PaymentInfo objects for recent transactions
        """
        pass
    
    @abstractmethod
    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """
        Get detailed information about a specific transaction.
        
        Args:
            transaction_id: The transaction ID/hash to look up
            
        Returns:
            PaymentInfo object if transaction exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate if a wallet address is valid for this network.
        
        Args:
            address: The wallet address to validate
            
        Returns:
            True if address is valid, False otherwise
        """
        pass
    
    def convert_to_main_unit(self, smallest_units: int) -> Decimal:
        """Convert from smallest units to main currency units."""
        return Decimal(smallest_units) / Decimal(self.units_per_token)
    
    def convert_to_smallest_units(self, main_units: Decimal) -> int:
        """Convert from main currency units to smallest units."""
        return int(main_units * Decimal(self.units_per_token))
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False
