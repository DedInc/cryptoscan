"""
Data models for CryptoScan
"""

from __future__ import annotations

__all__ = [
    "PaymentStatus",
    "MatchMode",
    "PaymentInfo",
    "PaymentEvent",
    "ErrorEvent",
    "TokenConfig",
    "match_amount",
]

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class PaymentStatus(Enum):
    """Payment transaction status"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class MatchMode(Enum):
    """Amount matching strategy for payment detection"""

    EXACT = "exact"
    AT_LEAST = "at_least"
    ANY = "any"


@dataclass(slots=True)
class TokenConfig:
    """ERC-20 token configuration for monitoring token transfers"""

    contract_address: str
    symbol: str
    decimals: int = 18


def match_amount(actual: Decimal, expected: Decimal | None, mode: MatchMode) -> bool:
    if mode == MatchMode.ANY:
        return True
    if expected is None:
        return False
    if mode == MatchMode.AT_LEAST:
        return actual.normalize() >= expected.normalize()
    return actual.normalize() == expected.normalize()


@dataclass(slots=True)
class PaymentInfo:
    """Payment information returned when a payment is detected"""

    transaction_id: str
    wallet_address: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    timestamp: datetime
    block_height: int | None = None
    confirmations: int = 0
    fee: Decimal | None = None
    from_address: str = ""
    to_address: str = ""
    token_contract: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PaymentEvent:
    """Event emitted when payment is detected"""

    payment_info: PaymentInfo
    monitor_id: str
    network: str
    detected_at: datetime = field(default_factory=_utc_now)


@dataclass
class ErrorEvent:
    """Event emitted when an error occurs"""

    error: Exception
    monitor_id: str
    network: str
    timestamp: datetime = field(default_factory=_utc_now)
    message: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            self.message = str(self.error)
