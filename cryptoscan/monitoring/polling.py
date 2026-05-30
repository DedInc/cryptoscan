"""Polling-based monitoring strategy."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from decimal import Decimal
from typing import TYPE_CHECKING

from ..core.config import UserConfig
from ..core.exceptions import NetworkError
from ..core.models import MatchMode, PaymentInfo, TokenConfig
from .strategies import ErrorCallback, MonitoringStrategy, PaymentCallback

if TYPE_CHECKING:
    from ..provider.universal_provider import UniversalProvider

logger = logging.getLogger(__name__)


class PollingStrategy(MonitoringStrategy):
    """Polling-based monitoring strategy"""

    def __init__(
        self,
        provider: UniversalProvider,
        wallet_address: str,
        expected_amount: Decimal | None,
        config: UserConfig,
        poll_interval: float,
        max_transactions: int,
        auto_stop: bool,
        min_confirmations: int = 1,
        match_mode: MatchMode = MatchMode.EXACT,
        token_contract: str | TokenConfig | None = None,
    ) -> None:
        super().__init__(
            provider,
            wallet_address,
            expected_amount,
            config,
            match_mode=match_mode,
            token_contract=token_contract,
        )
        self.poll_interval = poll_interval
        self.max_transactions = max_transactions
        self.auto_stop = auto_stop
        self.min_confirmations = min_confirmations
        self._start_timestamp: float | None = None
        self._seen_tx_ids: deque[str] = deque(maxlen=10000)

    async def monitor(
        self, payment_callback: PaymentCallback, error_callback: ErrorCallback
    ) -> None:
        """Poll for payments at regular intervals"""
        self._start_timestamp = time.time()
        logger.info(f"Starting polling monitor at timestamp {self._start_timestamp}")

        while not self._stop_event.is_set():
            try:
                payment = await self._find_payment_once()
                if payment and not self._should_skip_payment(payment):
                    should_stop = await self._handle_confirmed_payment(
                        payment, payment_callback
                    )
                    if should_stop:
                        break
                await self._sleep_until_next_poll()
            except NetworkError as e:
                logger.warning(f"Network error during polling: {e}")
                await error_callback(e)
                await asyncio.sleep(self.config.retry_delay)
            except Exception as e:
                logger.error(f"Unexpected error during polling: {e}")
                await error_callback(e)
                await asyncio.sleep(self.config.retry_delay)

    async def _find_payment_once(self) -> PaymentInfo | None:
        return await self.provider.find_payment(
            self.wallet_address,
            self.expected_amount,
            self.max_transactions,
            match_mode=self.match_mode,
            token_contract=self.token_contract,
        )

    def _should_skip_payment(self, payment: PaymentInfo) -> bool:
        if payment.transaction_id in self._seen_tx_ids:
            logger.debug(
                "Skipping already-seen transaction: %s...",
                payment.transaction_id[:16],
            )
            return True

        if payment.timestamp and self._start_timestamp:
            tx_timestamp = (
                payment.timestamp.timestamp()
                if hasattr(payment.timestamp, "timestamp")
                else float(payment.timestamp)
            )
            if tx_timestamp < self._start_timestamp:
                logger.debug(
                    "Skipping old transaction (before start): %s...",
                    payment.transaction_id[:16],
                )
                self._seen_tx_ids.append(payment.transaction_id)
                return True

        return False

    async def _handle_confirmed_payment(
        self, payment: PaymentInfo, payment_callback: PaymentCallback
    ) -> bool:
        if payment.confirmations < self.min_confirmations:
            logger.debug(
                "Payment found but insufficient confirmations: %s/%s",
                payment.confirmations,
                self.min_confirmations,
            )
            return False

        logger.info(
            "Payment found: %s %s (tx: %s..., confirmations: %s/%s)",
            payment.amount,
            payment.currency,
            payment.transaction_id[:16],
            payment.confirmations,
            self.min_confirmations,
        )
        self._seen_tx_ids.append(payment.transaction_id)
        await payment_callback(payment)
        return self.auto_stop

    async def _sleep_until_next_poll(self) -> None:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
