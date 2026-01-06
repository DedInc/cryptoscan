"""
Data models for CryptoScan
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class PaymentStatus(Enum):
    """Payment transaction status"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass(slots=True)
class PaymentInfo:
    """Payment information returned when a payment is detected"""

    transaction_id: str
    wallet_address: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    timestamp: datetime
    block_height: Optional[int] = None
    confirmations: int = 0
    fee: Optional[Decimal] = None
    from_address: str = ""
    to_address: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


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

    def __post_init__(self):
        if not self.message:
            self.message = str(self.error)
