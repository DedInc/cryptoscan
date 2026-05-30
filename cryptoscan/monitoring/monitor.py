"""PaymentMonitor class for CryptoScan"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING

from ..core.config import UserConfig
from ..core.models import MatchMode, PaymentInfo, TokenConfig
from .callbacks import emit_error_event, emit_payment_event
from .strategies import (
    WEBSOCKET_CHAIN_TYPES,
    MonitoringStrategy,
    PollingStrategy,
    RealtimeStrategy,
)

if TYPE_CHECKING:
    from ..provider.universal_provider import UniversalProvider

logger = logging.getLogger(__name__)


def _token_repr(token_contract: str | TokenConfig | None) -> str:
    if token_contract is None:
        return "native"
    if hasattr(token_contract, "contract_address"):
        return token_contract.contract_address[:10] + "..."
    return str(token_contract)[:10] + "..."


class PaymentMonitor:
    """
    Payment monitor for cryptocurrency transactions

    Features:
    - Async payment monitoring with polling
    - Event callbacks for payments and errors
    - Auto-stop after payment detection
    - Configurable poll intervals
    """

    def __init__(
        self,
        provider: UniversalProvider,
        wallet_address: str,
        expected_amount: str | Decimal | None = None,
        poll_interval: float = 15.0,
        max_transactions: int = 10,
        auto_stop: bool = False,
        monitor_id: str | None = None,
        user_config: UserConfig | None = None,
        realtime: bool = True,
        min_confirmations: int = 1,
        match_mode: MatchMode | str = MatchMode.EXACT,
        token_contract: str | TokenConfig | None = None,
    ) -> None:
        """
        Initialize payment monitor

        Args:
            provider: Network provider instance
            wallet_address: Wallet address to monitor
            expected_amount: Expected payment amount (None for MatchMode.ANY)
            poll_interval: Seconds between checks
            max_transactions: Max transactions to check per poll
            auto_stop: Stop monitoring after finding payment
            monitor_id: Optional monitor identifier
            user_config: User configuration
            realtime: Use WebSocket for real-time monitoring
            min_confirmations: Minimum confirmations required
            match_mode: Amount matching strategy (exact, at_least, any)
            token_contract: Optional ERC-20 token contract address to monitor
        """
        self.provider = provider
        self.wallet_address = wallet_address
        self.expected_amount = (
            Decimal(str(expected_amount)) if expected_amount is not None else None
        )
        self.poll_interval = poll_interval
        self.max_transactions = max_transactions
        self.auto_stop = auto_stop
        self.monitor_id = monitor_id or str(uuid.uuid4())
        self.config = user_config or UserConfig()
        self.realtime = realtime
        self.min_confirmations = min_confirmations
        self.match_mode = (
            match_mode if isinstance(match_mode, MatchMode) else MatchMode(match_mode)
        )
        self.token_contract = token_contract

        self._is_running = False
        self._payment_callbacks: list[Callable] = []
        self._error_callbacks: list[Callable] = []
        self._task: asyncio.Task | None = None
        self._strategy: MonitoringStrategy | None = None

    def on_payment(self, callback: Callable) -> Callable:
        """
        Register payment event handler

        Can be used as decorator:
        @monitor.on_payment
        async def handle_payment(event):
            ...

        Or as method:
        monitor.on_payment(handle_payment)
        """
        if callback not in self._payment_callbacks:
            self._payment_callbacks.append(callback)
        return callback

    def on_error(self, callback: Callable) -> Callable:
        """
        Register error event handler

        Can be used as decorator:
        @monitor.on_error
        async def handle_error(event):
            ...

        Or as method:
        monitor.on_error(handle_error)
        """
        if callback not in self._error_callbacks:
            self._error_callbacks.append(callback)
        return callback

    async def start(self) -> None:
        """Start payment monitoring"""
        if self._is_running:
            logger.warning(f"Monitor {self.monitor_id} is already running")
            return

        self._is_running = True
        mode = "real-time" if self.realtime else "polling"
        amount_repr = (
            str(self.expected_amount) if self.expected_amount is not None else "any"
        )
        logger.info(
            "Starting %s monitor %s for %s (%s..., %s %s, mode=%s, token=%s)",
            mode,
            self.monitor_id,
            self.provider.NETWORK_NAME,
            self.wallet_address[:16],
            amount_repr,
            self.provider.CURRENCY_SYMBOL,
            self.match_mode.value,
            _token_repr(self.token_contract),
        )

        try:
            await self.provider.connect()
            self._strategy = self._create_strategy()
            await self._strategy.monitor(self._emit_payment, self._emit_error)
        except Exception as e:
            logger.error(f"Monitor {self.monitor_id} failed: {e}")
            await self._emit_error(e)
            raise
        finally:
            self._is_running = False
            await self.provider.close()

    async def stop(self) -> None:
        """Stop payment monitoring"""
        if not self._is_running:
            return

        logger.info(f"Stopping monitor {self.monitor_id}")
        self._is_running = False

        if self._strategy:
            self._strategy.stop()

        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def _create_strategy(self) -> MonitoringStrategy:
        """Create appropriate monitoring strategy"""
        if self.realtime and self._can_use_realtime():
            return RealtimeStrategy(
                self.provider,
                self.wallet_address,
                self.expected_amount,
                self.config,
                self.auto_stop,
                self.min_confirmations,
                match_mode=self.match_mode,
                token_contract=self.token_contract,
            )
        else:
            return PollingStrategy(
                self.provider,
                self.wallet_address,
                self.expected_amount,
                self.config,
                self.poll_interval,
                self.max_transactions,
                self.auto_stop,
                self.min_confirmations,
                match_mode=self.match_mode,
                token_contract=self.token_contract,
            )

    async def _emit_payment(self, payment: PaymentInfo) -> None:
        """Emit payment event to all callbacks"""
        await emit_payment_event(
            payment,
            self.monitor_id,
            self.provider.NETWORK_NAME,
            self._payment_callbacks,
        )

    async def _emit_error(self, error: Exception) -> None:
        """Emit error event to all callbacks"""
        await emit_error_event(
            error, self.monitor_id, self.provider.NETWORK_NAME, self._error_callbacks
        )

    @property
    def is_running(self) -> bool:
        """Check if monitor is currently running"""
        return self._is_running

    def _can_use_realtime(self) -> bool:
        """Check if real-time monitoring is available for this network"""
        return (
            hasattr(self.provider, "network_config")
            and self.provider.network_config.ws_url is not None
            and self.provider.network_config.chain_type in WEBSOCKET_CHAIN_TYPES
        )

    def __repr__(self) -> str:
        status = "running" if self._is_running else "stopped"
        mode = "realtime" if self.realtime else "polling"
        return (
            f"PaymentMonitor("
            f"id={self.monitor_id}, "
            f"network={self.provider.NETWORK_NAME}, "
            f"address={self.wallet_address[:16]}..., "
            f"amount={self.expected_amount}, "
            f"mode={mode}, "
            f"status={status})"
        )
