"""Base adapter class for blockchain API adapters."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

__all__ = ["BaseAdapter", "MAX_RESPONSE_SIZE"]

from ..core.models import PaymentInfo
from ..security import validate_rpc_url

if TYPE_CHECKING:
    from ..networks import NetworkConfig

# Maximum response size (10MB) to prevent memory exhaustion
MAX_RESPONSE_SIZE = 10 * 1024 * 1024


class BaseAdapter:
    """Base class for API adapters"""

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0

    def __init__(
        self,
        rpc_url: str,
        network_config: NetworkConfig,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        self.rpc_url = rpc_url
        if not validate_rpc_url(rpc_url):
            from ..core.exceptions import ValidationError

            raise ValidationError(f"Invalid or unsafe RPC URL: {rpc_url}")
        self.network_config = network_config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.http_client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize HTTP client"""
        from ..core.config import DEFAULT_ADAPTER_TIMEOUT

        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                timeout=DEFAULT_ADAPTER_TIMEOUT, http2=True
            )

    def _get_retry_context(self) -> AsyncRetrying:
        """Get tenacity retry context for HTTP requests"""
        return AsyncRetrying(
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(
                multiplier=self.retry_delay,
                min=self.retry_delay,
                max=10,
            ),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPError)),
            reraise=True,
        )

    async def close(self) -> None:
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def __aenter__(self) -> BaseAdapter:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        await self.close()
        return False

    async def get_transactions(
        self, address: str, limit: int = 10
    ) -> list[PaymentInfo]:
        """Get transactions - must be implemented by subclass"""
        raise NotImplementedError

    async def get_transaction(self, tx_id: str) -> PaymentInfo | None:
        """Get single transaction - must be implemented by subclass"""
        raise NotImplementedError
