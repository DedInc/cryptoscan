"""
CryptoScan - Professional Async Crypto Payment Monitoring Library
Production-ready blockchain payment monitoring
"""

from .models import PaymentInfo, PaymentStatus, PaymentEvent, ErrorEvent
from .config import UserConfig, ProxyConfig, create_user_config
from .monitoring import PaymentMonitor
from .factory import create_monitor, get_supported_networks, get_provider
from .exceptions import (
    NetworkError,
    PaymentNotFoundError,
    CryptoScanError,
    ValidationError,
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

__version__ = "2.0.0"
__all__ = [
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
]
