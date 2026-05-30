"""WebSocket-based real-time monitoring strategy."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from ..core.config import UserConfig
from ..core.models import MatchMode, PaymentInfo, TokenConfig
from ..security import mask_url
from ..websocket import WebSocketClient
from .strategies import ErrorCallback, MonitoringStrategy, PaymentCallback

if TYPE_CHECKING:
    from ..provider.universal_provider import UniversalProvider

logger = logging.getLogger(__name__)


class RealtimeStrategy(MonitoringStrategy):
    """WebSocket-based real-time monitoring strategy"""

    def __init__(
        self,
        provider: UniversalProvider,
        wallet_address: str,
        expected_amount: Decimal | None,
        config: UserConfig,
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
        self.auto_stop = auto_stop
        self.min_confirmations = min_confirmations
        self._ws_client: WebSocketClient | None = None
        self._listen_task: asyncio.Task | None = None
        self._payment_callback: PaymentCallback | None = None
        self._error_callback: ErrorCallback | None = None
        self._start_block: int | None = None

    async def monitor(
        self, payment_callback: PaymentCallback, error_callback: ErrorCallback
    ) -> None:
        """Monitor using WebSocket subscriptions"""
        self._payment_callback = payment_callback
        self._error_callback = error_callback

        try:
            self._start_block = await self.provider.get_block_number()
            logger.info(f"Starting real-time monitor from block #{self._start_block}")
        except Exception as e:
            logger.warning(f"Could not get current block number: {e}")
            self._start_block = 0

        ws_url = self.provider.network_config.ws_url
        logger.info(f"Starting real-time block monitoring on {mask_url(ws_url)}")

        try:
            self._ws_client = WebSocketClient(ws_url, self.config)
            await self._ws_client.connect()
            await self._ws_client.subscribe_new_heads(self._on_new_block)
            self._listen_task = asyncio.create_task(self._ws_client.listen())
            await self._stop_event.wait()
        except Exception as e:
            logger.error(f"Real-time monitoring error: {e}")
            await error_callback(e)
            raise
        finally:
            await self._cleanup()

    async def _on_new_block(self, block_header: dict) -> None:
        """Handle new block notification"""
        if not block_header:
            logger.debug("Received empty block header, skipping")
            return

        try:
            block_number = int(block_header.get("number", "0x0"), 16)

            if self._start_block and block_number <= self._start_block:
                logger.debug(
                    "Skipping old block #%s (started at #%s)",
                    block_number,
                    self._start_block,
                )
                return

            logger.debug(f"New block #{block_number} on {self.provider.NETWORK_NAME}")

            payment = await self._check_block_for_payment(block_header)
            if payment:
                if payment.confirmations >= self.min_confirmations:
                    logger.info(
                        "Payment in new block! Amount: %s, confirmations: %s/%s",
                        payment.amount,
                        payment.confirmations,
                        self.min_confirmations,
                    )
                    await self._payment_callback(payment)
                    if self.auto_stop:
                        self.stop()
                else:
                    logger.debug(
                        "Payment detected but insufficient confirmations: %s/%s",
                        payment.confirmations,
                        self.min_confirmations,
                    )
        except Exception as e:
            logger.error(f"Error processing new block: {e}")
            await self._error_callback(e)

    async def _check_block_for_payment(self, block_header: dict) -> PaymentInfo | None:
        """Check if block contains the expected payment."""
        block_hash = block_header.get("hash")
        if not block_hash:
            return None

        try:
            return await self.provider.get_block_for_payment(
                block_hash,
                self.wallet_address,
                self.expected_amount,
                match_mode=self.match_mode,
                token_contract=self.token_contract,
            )
        except Exception as e:
            logger.error(f"Error checking block for payment: {e}")

        return None

    async def _cleanup(self) -> None:
        """Clean up WebSocket resources"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task

        if self._ws_client:
            await self._ws_client.close()
            self._ws_client = None
