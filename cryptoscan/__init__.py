"""
CryptoScan - Professional Async Crypto Payment Monitoring Library
Production-ready blockchain payment monitoring
"""

from ._version import __version__
from .models import PaymentInfo, PaymentStatus, PaymentEvent, ErrorEvent
from .config import UserConfig, ProxyConfig, create_user_config
from .monitoring import PaymentMonitor
from .factory import create_monitor, get_supported_networks, get_provider
from .exceptions import (
    NetworkError,
    PaymentNotFoundError,
    CryptoScanError,
    ValidationError,
    ParserError,
    BlockFetchError,
    AdapterError,
    RPCError,
)
from .security import (
    validate_rpc_url,
    validate_ws_url,
    mask_address,
    mask_transaction_id,
)
from .metrics import (
    MetricsCollector,
    RequestMetric,
    MetricsSummary,
    get_global_metrics,
    enable_global_metrics,
    disable_global_metrics,
)
from .config import (
    MAX_BLOCKS_TO_SCAN,
    BLOCKS_PER_TX_MULTIPLIER,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAX_RETRIES,
)
from .universal_provider import UniversalProvider
from .networks import (
    NetworkConfig,
    get_network,
    list_networks,
    register_network,
    create_network_config,
    register_common_networks,
)

# Register common networks automatically
register_common_networks()

__all__ = [
    # Version
    "__version__",
    # Core API
    "create_monitor",
    "get_supported_networks",
    "get_provider",
    "get_network",
    "list_networks",
    "register_network",
    "create_network_config",
    "PaymentMonitor",
    # Universal Provider
    "UniversalProvider",
    "NetworkConfig",
    # Configuration
    "UserConfig",
    "ProxyConfig",
    "create_user_config",
    # Constants
    "MAX_BLOCKS_TO_SCAN",
    "BLOCKS_PER_TX_MULTIPLIER",
    "DEFAULT_HTTP_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    # Models
    "PaymentInfo",
    "PaymentStatus",
    "PaymentEvent",
    "ErrorEvent",
    # Exceptions
    "NetworkError",
    "PaymentNotFoundError",
    "ValidationError",
    "CryptoScanError",
    "ParserError",
    "BlockFetchError",
    "AdapterError",
    "RPCError",
    # Security utilities
    "validate_rpc_url",
    "validate_ws_url",
    "mask_address",
    "mask_transaction_id",
    # Metrics
    "MetricsCollector",
    "RequestMetric",
    "MetricsSummary",
    "get_global_metrics",
    "enable_global_metrics",
    "disable_global_metrics",
]
