"""PaymentMonitor class for CryptoScan"""

import asyncio
import logging
import uuid
from decimal import Decimal
from typing import Callable, Optional, Union

from ..config import UserConfig
from ..exceptions import CryptoScanError
from ..models import PaymentEvent, ErrorEvent, PaymentInfo
from .strategies import PollingStrategy, RealtimeStrategy


logger = logging.getLogger(__name__)


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
        provider,  # UniversalProvider (avoid circular import)
        wallet_address: str,
        expected_amount: Union[str, Decimal],
        poll_interval: float = 15.0,
        max_transactions: int = 10,
        auto_stop: bool = False,
        monitor_id: Optional[str] = None,
        user_config: Optional[UserConfig] = None,
        realtime: bool = True,  # Use WebSocket for real-time monitoring
        min_confirmations: int = 1  # Minimum confirmations required
    ):
        """
        Initialize payment monitor
        
        Args:
            provider: Network provider instance
            wallet_address: Wallet address to monitor
            expected_amount: Expected payment amount (exact match)
            poll_interval: Seconds between checks
            max_transactions: Max transactions to check per poll
            auto_stop: Stop monitoring after finding payment
            monitor_id: Optional monitor identifier
            user_config: User configuration
        """
        self.provider = provider
        self.wallet_address = wallet_address
        self.expected_amount = Decimal(str(expected_amount))
        self.poll_interval = poll_interval
        self.max_transactions = max_transactions
        self.auto_stop = auto_stop
        self.monitor_id = monitor_id or str(uuid.uuid4())
        self.config = user_config or UserConfig()
        self.realtime = realtime
        self.min_confirmations = min_confirmations
        
        self._is_running = False
        self._payment_callbacks = []
        self._error_callbacks = []
        self._task: Optional[asyncio.Task] = None
        self._strategy = None
    
    def on_payment(self, callback: Callable):
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
    
    def on_error(self, callback: Callable):
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
    
    async def start(self):
        """Start payment monitoring"""
        if self._is_running:
            logger.warning(f"Monitor {self.monitor_id} is already running")
            return
        
        self._is_running = True
        mode = "real-time" if self.realtime else "polling"
        logger.info(
            f"Starting {mode} monitor {self.monitor_id} for {self.provider.NETWORK_NAME} "
            f"({self.wallet_address[:16]}..., {self.expected_amount} {self.provider.CURRENCY_SYMBOL})"
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
    
    async def stop(self):
        """Stop payment monitoring"""
        if not self._is_running:
            return
        
        logger.info(f"Stopping monitor {self.monitor_id}")
        self._is_running = False
        
        if self._strategy:
            self._strategy.stop()
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def _create_strategy(self):
        """Create appropriate monitoring strategy"""
        if self.realtime and self._can_use_realtime():
            return RealtimeStrategy(
                self.provider,
                self.wallet_address,
                self.expected_amount,
                self.config,
                self.auto_stop,
                self.min_confirmations
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
                self.min_confirmations
            )
    
    async def _emit_payment(self, payment: PaymentInfo):
        """Emit payment event to all callbacks"""
        event = PaymentEvent(
            payment_info=payment,
            monitor_id=self.monitor_id,
            network=self.provider.NETWORK_NAME
        )
        
        for callback in self._payment_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in payment callback: {e}")
    
    async def _emit_error(self, error: Exception):
        """Emit error event to all callbacks"""
        event = ErrorEvent(
            error=error,
            monitor_id=self.monitor_id,
            network=self.provider.NETWORK_NAME
        )
        
        for callback in self._error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if monitor is currently running"""
        return self._is_running
    
    def _can_use_realtime(self) -> bool:
        """Check if real-time monitoring is available for this network"""
        return (
            hasattr(self.provider, 'network_config') and 
            self.provider.network_config.ws_url is not None and
            self.provider.network_config.chain_type in ['evm', 'solana']
        )
    
    def __repr__(self):
        status = "running" if self._is_running else "stopped"
        mode = "realtime" if self.realtime else "polling"
        return (
            f"PaymentMonitor(id={self.monitor_id}, network={self.provider.NETWORK_NAME}, "
            f"address={self.wallet_address[:16]}..., amount={self.expected_amount}, mode={mode}, status={status})"
        )
