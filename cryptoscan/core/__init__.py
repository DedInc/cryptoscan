"""Core domain types: configuration, exceptions, and data models."""

from .config import ProxyConfig, UserConfig, create_user_config
from .exceptions import (
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
from .models import (
    ErrorEvent,
    MatchMode,
    PaymentEvent,
    PaymentInfo,
    PaymentStatus,
    TokenConfig,
    match_amount,
)

__all__ = [
    "ProxyConfig",
    "UserConfig",
    "create_user_config",
    "CryptoScanError",
    "NetworkError",
    "CSConnectionError",
    "CSTimeoutError",
    "PaymentNotFoundError",
    "ValidationError",
    "RPCError",
    "ParserError",
    "BlockFetchError",
    "AdapterError",
    "PaymentStatus",
    "MatchMode",
    "PaymentInfo",
    "PaymentEvent",
    "ErrorEvent",
    "TokenConfig",
    "match_amount",
]
