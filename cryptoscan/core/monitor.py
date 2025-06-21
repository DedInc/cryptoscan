"""
Payment Monitor - Core monitoring functionality for CryptoScan

Provides the main PaymentMonitor class that orchestrates payment detection
across different cryptocurrency networks.
"""

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Set, Callable, Awaitable
import logging

from .base import BaseNetworkProvider, PaymentInfo, PaymentStatus
from .events import EventEmitter, EventType, PaymentEvent, MonitorEvent, ErrorEvent
from ..exceptions import CryptoScanError, ValidationError


logger = logging.getLogger(__name__)


class PaymentMonitor:
    """
    Main payment monitoring class that coordinates payment detection
    across different cryptocurrency networks.
    
    Features:
    - Async payment monitoring with configurable polling intervals
    - Event-driven architecture with callbacks
    - Automatic duplicate transaction filtering
    - Flexible amount matching with tolerance
    - Comprehensive error handling and retry logic
    """
    
    def __init__(
        self,
        provider: BaseNetworkProvider,
        wallet_address: str,
        expected_amount: str | Decimal,
        poll_interval: float = 15.0,
        max_transactions: int = 10,
        auto_stop: bool = False,
        monitor_id: Optional[str] = None
    ):
        """
        Initialize the payment monitor.

        Args:
            provider: Network provider instance (e.g., SolanaProvider)
            wallet_address: Wallet address to monitor for payments
            expected_amount: Expected payment amount
            poll_interval: Seconds between polling cycles
            max_transactions: Maximum transactions to check per poll
            auto_stop: Whether to automatically stop after finding a payment
            monitor_id: Unique identifier for this monitor instance
        """
        self.provider = provider
        self.wallet_address = wallet_address
        self.expected_amount = Decimal(str(expected_amount))
        self.poll_interval = poll_interval
        self.max_transactions = max_transactions
        self.auto_stop = auto_stop
        self.monitor_id = monitor_id or str(uuid.uuid4())
        
        # Event system
        self.events = EventEmitter()
        
        # State tracking
        self._is_running = False
        self._should_stop = False
        self._processed_transactions: Set[str] = set()
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate monitor configuration."""
        if self.expected_amount <= 0:
            raise ValidationError("Expected amount must be positive")

        if self.poll_interval <= 0:
            raise ValidationError("Poll interval must be positive")

        if self.max_transactions <= 0:
            raise ValidationError("Max transactions must be positive")
    
    def on_payment(self, callback: Callable[[PaymentEvent], Awaitable[None]]) -> None:
        """
        Register a callback for payment detection events.
        
        Args:
            callback: Async function to call when payment is detected
        """
        self.events.on(EventType.PAYMENT_DETECTED, callback)
    
    def on_confirmed_payment(self, callback: Callable[[PaymentEvent], Awaitable[None]]) -> None:
        """
        Register a callback for confirmed payment events.
        
        Args:
            callback: Async function to call when payment is confirmed
        """
        self.events.on(EventType.PAYMENT_CONFIRMED, callback)
    
    def on_error(self, callback: Callable[[ErrorEvent], Awaitable[None]]) -> None:
        """
        Register a callback for error events.
        
        Args:
            callback: Async function to call when errors occur
        """
        self.events.on(EventType.ERROR_OCCURRED, callback)
    
    def on_start(self, callback: Callable[[MonitorEvent], Awaitable[None]]) -> None:
        """
        Register a callback for monitor start events.
        
        Args:
            callback: Async function to call when monitoring starts
        """
        self.events.on(EventType.MONITOR_STARTED, callback)
    
    def on_stop(self, callback: Callable[[MonitorEvent], Awaitable[None]]) -> None:
        """
        Register a callback for monitor stop events.
        
        Args:
            callback: Async function to call when monitoring stops
        """
        self.events.on(EventType.MONITOR_STOPPED, callback)
    
    async def start(self) -> None:
        """Start the payment monitoring process."""
        if self._is_running:
            raise CryptoScanError("Monitor is already running")
        
        # Validate wallet address
        if not await self.provider.validate_wallet_address(self.wallet_address):
            raise ValidationError(f"Invalid wallet address: {self.wallet_address}")
        
        self._is_running = True
        self._should_stop = False
        
        # Emit start event
        start_event = MonitorEvent(
            event_type=EventType.MONITOR_STARTED,
            timestamp=datetime.utcnow(),
            monitor_id=self.monitor_id,
            details={
                "wallet_address": self.wallet_address,
                "expected_amount": str(self.expected_amount),
                "currency": self.provider.currency_symbol,
                "network": self.provider.network_name
            }
        )
        await self.events.emit(EventType.MONITOR_STARTED, start_event)
        
        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info(
            f"Started monitoring wallet {self.wallet_address} for "
            f"{self.expected_amount} {self.provider.currency_symbol} "
            f"on {self.provider.network_name}"
        )
    
    async def stop(self) -> None:
        """Stop the payment monitoring process."""
        if not self._is_running:
            return

        logger.info(f"Stopping monitor for wallet {self.wallet_address}")
        self._is_running = False
        self._should_stop = True

        # Cancel monitoring task gracefully
        if self._monitor_task and not self._monitor_task.done():
            logger.debug("Cancelling monitor task...")
            self._monitor_task.cancel()
            try:
                # Wait for task to complete cancellation
                await asyncio.wait_for(self._monitor_task, timeout=2.0)
            except asyncio.CancelledError:
                logger.debug("Monitor task cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Monitor task cancellation timed out")
            except Exception as e:
                logger.error(f"Error during task cancellation: {e}")

        # Close provider session
        try:
            await self.provider.close()
            logger.debug("Provider session closed")
        except Exception as e:
            logger.error(f"Error closing provider session: {e}")

        # Emit stop event
        try:
            stop_event = MonitorEvent(
                event_type=EventType.MONITOR_STOPPED,
                timestamp=datetime.utcnow(),
                monitor_id=self.monitor_id
            )
            await self.events.emit(EventType.MONITOR_STOPPED, stop_event)
        except Exception as e:
            logger.error(f"Error emitting stop event: {e}")

        logger.info(f"Stopped monitoring wallet {self.wallet_address}")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        try:
            while self._is_running and not self._should_stop:
                try:
                    await self._check_for_payments()
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")

                    # Emit error event
                    error_event = ErrorEvent(
                        event_type=EventType.ERROR_OCCURRED,
                        error=e,
                        timestamp=datetime.utcnow(),
                        monitor_id=self.monitor_id,
                        context={"wallet_address": self.wallet_address}
                    )
                    await self.events.emit(EventType.ERROR_OCCURRED, error_event)

                # Check if we should stop before sleeping
                if self._is_running and not self._should_stop:
                    try:
                        await asyncio.sleep(self.poll_interval)
                    except asyncio.CancelledError:
                        logger.debug("Monitor loop cancelled during sleep")
                        break
        except asyncio.CancelledError:
            logger.debug("Monitor loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in monitor loop: {e}")
        finally:
            logger.debug("Monitor loop finished")
    
    async def _check_for_payments(self) -> None:
        """Check for new payments matching our criteria."""
        check_start_time = asyncio.get_running_loop().time()
        logger.info(f"🔍 Starting payment check for wallet {self.wallet_address}")
        logger.debug(f"   Expected amount: {self.expected_amount} {self.provider.currency_symbol}")
        logger.debug(f"   Max transactions to check: {self.max_transactions}")

        try:
            # Get recent transactions with detailed logging
            logger.debug(f"📡 Fetching recent transactions from {self.provider.network_name}...")
            transactions = await self.provider.get_recent_transactions(
                self.wallet_address,
                self.max_transactions
            )

            fetch_time = asyncio.get_running_loop().time() - check_start_time
            logger.info(f"📊 Retrieved {len(transactions)} transactions in {fetch_time:.2f}s")

            if not transactions:
                logger.info("📭 No transactions found")
                return

            # Process each transaction with detailed logging
            new_transactions = 0
            skipped_transactions = 0
            matching_payments = 0

            for i, payment in enumerate(transactions, 1):
                logger.debug(f"🔍 Processing transaction {i}/{len(transactions)}: {payment.transaction_id[:16]}...")

                # Skip already processed transactions
                if payment.transaction_id in self._processed_transactions:
                    skipped_transactions += 1
                    logger.debug(f"   ⏭️  Already processed, skipping")
                    continue

                new_transactions += 1
                logger.info(f"🆕 New transaction found: {payment.transaction_id}")
                logger.info(f"   💰 Amount: {payment.amount} {payment.currency}")
                logger.info(f"   📅 Timestamp: {payment.timestamp}")
                logger.info(f"   📊 Status: {payment.status.value}")
                if payment.block_height:
                    logger.info(f"   🧱 Block: {payment.block_height}")
                if payment.confirmations:
                    logger.info(f"   ✅ Confirmations: {payment.confirmations}")
                if payment.fee:
                    logger.info(f"   💸 Fee: {payment.fee} {payment.currency}")

                # Mark as processed
                self._processed_transactions.add(payment.transaction_id)

                # Check if amount matches our criteria
                if self._is_matching_payment(payment):
                    matching_payments += 1
                    logger.info(f"🎉 MATCHING PAYMENT FOUND!")
                    await self._handle_matching_payment(payment)
                else:
                    logger.debug(f"   ❌ Amount doesn't match criteria")

            # Summary logging
            total_time = asyncio.get_running_loop().time() - check_start_time
            logger.info(f"📈 Check completed in {total_time:.2f}s:")
            logger.info(f"   📊 Total transactions: {len(transactions)}")
            logger.info(f"   🆕 New transactions: {new_transactions}")
            logger.info(f"   ⏭️  Skipped (already processed): {skipped_transactions}")
            logger.info(f"   🎯 Matching payments: {matching_payments}")
            logger.info(f"   🗃️  Total processed so far: {len(self._processed_transactions)}")

        except Exception as e:
            logger.error(f"❌ Error checking for payments: {e}")
            logger.debug(f"   Wallet: {self.wallet_address}")
            logger.debug(f"   Provider: {self.provider.network_name}")
            logger.debug(f"   RPC URL: {self.provider.config.rpc_url}")
            raise
    
    def _is_matching_payment(self, payment: PaymentInfo) -> bool:
        """Check if a payment matches our expected criteria."""
        return payment.amount == self.expected_amount
    
    async def _handle_matching_payment(self, payment: PaymentInfo) -> None:
        """Handle a payment that matches our criteria."""
        logger.info(
            f"Matching payment detected: {payment.amount} {self.provider.currency_symbol} "
            f"in transaction {payment.transaction_id}"
        )
        
        # Create payment event
        payment_event = PaymentEvent(
            event_type=EventType.PAYMENT_DETECTED,
            payment_info=payment,
            timestamp=datetime.utcnow(),
            monitor_id=self.monitor_id,
            additional_data={
                "expected_amount": str(self.expected_amount),
                "amount_difference": str(abs(payment.amount - self.expected_amount))
            }
        )
        
        # Emit payment detected event
        await self.events.emit(EventType.PAYMENT_DETECTED, payment_event)

        # If payment is confirmed, emit confirmed event
        if payment.status == PaymentStatus.CONFIRMED:
            confirmed_event = PaymentEvent(
                event_type=EventType.PAYMENT_CONFIRMED,
                payment_info=payment,
                timestamp=datetime.utcnow(),
                monitor_id=self.monitor_id
            )
            await self.events.emit(EventType.PAYMENT_CONFIRMED, confirmed_event)

        # Auto-stop after finding payment if enabled
        if self.auto_stop:
            logger.info(f"Auto-stopping monitor after payment found")
            self._should_stop = True

    @property
    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._is_running
    
    @property
    def processed_count(self) -> int:
        """Get the number of processed transactions."""
        return len(self._processed_transactions)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
