"""
Monitoring strategies for payment detection
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import TYPE_CHECKING

from ..core.config import UserConfig
from ..core.models import MatchMode, PaymentInfo, TokenConfig

if TYPE_CHECKING:
    from ..provider.universal_provider import UniversalProvider

PaymentCallback = Callable[[PaymentInfo], Awaitable[None]]
ErrorCallback = Callable[[Exception], Awaitable[None]]

logger = logging.getLogger(__name__)

WEBSOCKET_CHAIN_TYPES: set[str] = {"evm"}


def register_websocket_chain_type(chain_type: str) -> None:
    WEBSOCKET_CHAIN_TYPES.add(chain_type)


class MonitoringStrategy(ABC):
    """Base class for monitoring strategies"""

    def __init__(
        self,
        provider: UniversalProvider,
        wallet_address: str,
        expected_amount: Decimal | None,
        config: UserConfig,
        match_mode: MatchMode = MatchMode.EXACT,
        token_contract: str | TokenConfig | None = None,
    ) -> None:
        self.provider = provider
        self.wallet_address = wallet_address
        self.expected_amount = expected_amount
        self.config = config
        self.match_mode = match_mode
        self.token_contract = token_contract
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def monitor(
        self, payment_callback: PaymentCallback, error_callback: ErrorCallback
    ) -> None:
        """Execute monitoring strategy"""
        pass

    def stop(self) -> None:
        """Signal strategy to stop"""
        self._stop_event.set()


from .polling import PollingStrategy  # noqa: E402
from .realtime import RealtimeStrategy  # noqa: E402

__all__ = [
    "MonitoringStrategy",
    "PollingStrategy",
    "RealtimeStrategy",
    "PaymentCallback",
    "ErrorCallback",
    "WEBSOCKET_CHAIN_TYPES",
    "register_websocket_chain_type",
]
