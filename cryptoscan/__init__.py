"""
CryptoScan - Professional Async Crypto Payment Monitoring Library
Production-ready blockchain payment monitoring
"""

from ._version import __version__
from .core.config import (
    BLOCKS_PER_TX_MULTIPLIER,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    MAX_BLOCKS_TO_SCAN,
    ProxyConfig,
    UserConfig,
    create_user_config,
)
from .core.exceptions import (
    AdapterError,
    BlockFetchError,
    CryptoScanError,
    CSConnectionError,
    CSTimeoutError,
    NetworkError,
    ParserError,
    PaymentNotFoundError,
    RPCError,
    ValidationError,
)
from .core.models import (
    ErrorEvent,
    MatchMode,
    PaymentEvent,
    PaymentInfo,
    PaymentStatus,
    TokenConfig,
    match_amount,
)
from .factory import create_monitor, get_provider, get_supported_networks
from .metrics import (
    MetricsCollector,
    MetricsSummary,
    RequestMetric,
    disable_global_metrics,
    enable_global_metrics,
    get_global_metrics,
)
from .monitoring import PaymentMonitor
from .monitoring.strategies import register_websocket_chain_type
from .networks import (
    NetworkConfig,
    create_network_config,
    get_network,
    list_networks,
    register_common_networks,
    register_network,
)
from .parsers import ChainParser
from .provider.universal_provider import (
    PARSER_REGISTRY,
    UniversalProvider,
    amounts_match,
    register_parser,
)
from .security import (
    mask_address,
    mask_transaction_id,
    mask_url,
    validate_rpc_url,
    validate_ws_url,
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
    "register_parser",
    "PARSER_REGISTRY",
    "ChainParser",
    # Monitoring extensions
    "register_websocket_chain_type",
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
    "MatchMode",
    "TokenConfig",
    "PaymentEvent",
    "ErrorEvent",
    # Exceptions
    "NetworkError",
    "CSConnectionError",
    "CSTimeoutError",
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
    "mask_url",
    # Provider utilities
    "amounts_match",
    "match_amount",
    # Metrics
    "MetricsCollector",
    "RequestMetric",
    "MetricsSummary",
    "get_global_metrics",
    "enable_global_metrics",
    "disable_global_metrics",
]
