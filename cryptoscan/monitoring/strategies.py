"""
Monitoring strategies for payment detection
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from ..config import UserConfig
from ..exceptions import NetworkError
from ..models import PaymentInfo

logger = logging.getLogger(__name__)


class MonitoringStrategy(ABC):
    """Base class for monitoring strategies"""

    def __init__(
        self,
        provider,
        wallet_address: str,
        expected_amount: Decimal,
        config: UserConfig,
    ):
        self.provider = provider
        self.wallet_address = wallet_address
        self.expected_amount = expected_amount
        self.config = config
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def monitor(self, payment_callback, error_callback) -> None:
        """Execute monitoring strategy"""
        pass

    def stop(self):
        """Signal strategy to stop"""
        self._stop_event.set()


class PollingStrategy(MonitoringStrategy):
    """Polling-based monitoring strategy"""

    def __init__(
        self,
        provider,
        wallet_address: str,
        expected_amount: Decimal,
        config: UserConfig,
        poll_interval: float,
        max_transactions: int,
        auto_stop: bool,
        min_confirmations: int = 1,
    ):
        super().__init__(provider, wallet_address, expected_amount, config)
        self.poll_interval = poll_interval
        self.max_transactions = max_transactions
        self.auto_stop = auto_stop
        self.min_confirmations = min_confirmations
        self._start_timestamp = None  # Track when monitoring started
        self._seen_tx_ids = set()  # Track already-seen transactions

    async def monitor(self, payment_callback, error_callback) -> None:
        """Poll for payments at regular intervals"""
        import time

        self._start_timestamp = time.time()
        logger.info(f"Starting polling monitor at timestamp {self._start_timestamp}")

        while not self._stop_event.is_set():
            try:
                payment = await self.provider.find_payment(
                    self.wallet_address, self.expected_amount, self.max_transactions
                )

                if payment:
                    # Skip if we've already seen this transaction
                    if payment.transaction_id in self._seen_tx_ids:
                        logger.debug(
                            f"Skipping already-seen transaction: {payment.transaction_id[:16]}..."
                        )
                        continue

                    # Skip transactions that occurred before monitor started
                    if payment.timestamp and self._start_timestamp:
                        tx_timestamp = (
                            payment.timestamp.timestamp()
                            if hasattr(payment.timestamp, "timestamp")
                            else float(payment.timestamp)
                        )
                        if tx_timestamp < self._start_timestamp:
                            logger.debug(
                                f"Skipping old transaction from before monitor started: {payment.transaction_id[:16]}..."
                            )
                            self._seen_tx_ids.add(payment.transaction_id)
                            continue

                    # Check if payment has sufficient confirmations
                    if payment.confirmations >= self.min_confirmations:
                        logger.info(
                            f"Payment found: {payment.amount} {payment.currency} "
                            f"(tx: {payment.transaction_id[:16]}..., confirmations: {payment.confirmations}/{self.min_confirmations})"
                        )
                        self._seen_tx_ids.add(payment.transaction_id)
                        await payment_callback(payment)

                        if self.auto_stop:
                            break
                    else:
                        logger.debug(
                            f"Payment found but insufficient confirmations: {payment.confirmations}/{self.min_confirmations}"
                        )

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self.poll_interval
                    )
                except asyncio.TimeoutError:
                    pass

            except NetworkError as e:
                logger.warning(f"Network error during polling: {e}")
                await error_callback(e)
                await asyncio.sleep(self.config.retry_delay)

            except Exception as e:
                logger.error(f"Unexpected error during polling: {e}")
                await error_callback(e)
                await asyncio.sleep(self.config.retry_delay)


class RealtimeStrategy(MonitoringStrategy):
    """WebSocket-based real-time monitoring strategy"""

    def __init__(
        self,
        provider,
        wallet_address: str,
        expected_amount: Decimal,
        config: UserConfig,
        auto_stop: bool,
        min_confirmations: int = 1,
    ):
        super().__init__(provider, wallet_address, expected_amount, config)
        self.auto_stop = auto_stop
        self.min_confirmations = min_confirmations
        self._ws_client = None
        self._listen_task = None
        self._payment_callback = None
        self._error_callback = None
        self._start_block = None  # Track starting block to ignore old transactions

    async def monitor(self, payment_callback, error_callback) -> None:
        """Monitor using WebSocket subscriptions"""
        import importlib.util

        from ..websocket_client import WebSocketClient

        if importlib.util.find_spec("websockets") is None:
            raise RuntimeError("websockets library not available")

        self._payment_callback = payment_callback
        self._error_callback = error_callback

        # Get current block number to only monitor NEW transactions from this point
        try:
            current_block = await self.provider.client.call("eth_blockNumber", [])
            self._start_block = int(current_block, 16)
            logger.info(f"Starting real-time monitor from block #{self._start_block}")
        except Exception as e:
            logger.warning(f"Could not get current block number: {e}")
            self._start_block = 0

        ws_url = self.provider.network_config.ws_url
        logger.info(f"Starting real-time block monitoring on {ws_url}")

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

    async def _on_new_block(self, block_header: dict):
        """Handle new block notification"""
        if not block_header:
            logger.debug("Received empty block header, skipping")
            return

        try:
            block_number = int(block_header.get("number", "0x0"), 16)

            # Only process blocks that arrived after monitor started
            if self._start_block and block_number <= self._start_block:
                logger.debug(
                    f"Skipping old block #{block_number} (started at #{self._start_block})"
                )
                return

            logger.debug(f"New block #{block_number} on {self.provider.NETWORK_NAME}")

            payment = await self._check_block_for_payment(block_header)
            if payment:
                # Check if payment has sufficient confirmations
                if payment.confirmations >= self.min_confirmations:
                    logger.info(
                        f"Payment detected in new block! Amount: {payment.amount}, "
                        f"confirmations: {payment.confirmations}/{self.min_confirmations}"
                    )
                    await self._payment_callback(payment)

                    if self.auto_stop:
                        self.stop()
                else:
                    logger.debug(
                        f"Payment detected but insufficient confirmations: {payment.confirmations}/{self.min_confirmations}"
                    )

        except Exception as e:
            logger.error(f"Error processing new block: {e}")
            await self._error_callback(e)

    async def _check_block_for_payment(
        self, block_header: dict
    ) -> Optional[PaymentInfo]:
        """Check if block contains the expected payment"""
        block_hash = block_header.get("hash")
        if not block_hash:
            return None

        try:
            block = await self.provider.client.call(
                "eth_getBlockByHash", [block_hash, True]
            )

            if not block or not block.get("transactions"):
                return None

            for tx in block["transactions"]:
                to_addr = tx.get("to") or ""
                if to_addr.lower() == self.wallet_address.lower():
                    value_wei = int(tx.get("value", "0x0"), 16)
                    amount = Decimal(value_wei) / Decimal(
                        10**self.provider.network_config.decimals
                    )

                    # Compare with proper precision (normalize both values)
                    if amount.normalize() == self.expected_amount.normalize():
                        return self.provider._parse_evm_tx(tx, block)

        except Exception as e:
            logger.error(f"Error checking block for payment: {e}")

        return None

    async def _cleanup(self):
        """Clean up WebSocket resources"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws_client:
            await self._ws_client.close()
            self._ws_client = None
