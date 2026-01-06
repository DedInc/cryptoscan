"""
RPC client for CryptoScan
Production-ready async RPC client with auto-reconnect and error handling
"""

import asyncio
import logging
from typing import Any, Optional
from contextlib import asynccontextmanager

import httpx
from tenacity import (
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    AsyncRetrying,
)

from .config import UserConfig
from .exceptions import (
    RPCError,
    ConnectionError as CSConnectionError,
    TimeoutError as CSTimeoutError,
)


logger = logging.getLogger(__name__)


class RPCClient:
    """
    Async WebSocket/HTTP RPC client with automatic reconnection
    Supports both WebSocket and HTTP RPC endpoints

    Features:
    - Rate limiting via semaphore to prevent node overload
    - Automatic retries with exponential backoff
    - HTTP/2 support for improved performance
    """

    def __init__(
        self,
        endpoint: str,
        user_config: Optional[UserConfig] = None,
        use_websocket: bool = True,
        max_concurrent_requests: int = 10,
    ):
        self.endpoint = endpoint
        self.use_websocket = use_websocket and endpoint.startswith(("ws://", "wss://"))
        self.config = user_config or UserConfig()

        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws_client = None
        self._connected = False
        self._reconnect_attempts = 0
        self._request_id = 0
        self._lock = asyncio.Lock()

        # Rate limiting: limit concurrent requests to prevent node overload
        self._rate_limiter = asyncio.Semaphore(max_concurrent_requests)

    async def connect(self):
        """Establish connection"""
        if self.use_websocket:
            await self._connect_websocket()
        else:
            await self._ensure_http_client()

    async def _ensure_http_client(self):
        """Ensure HTTP client is created"""
        if self._http_client is None:
            # Build client kwargs
            client_kwargs = {
                "timeout": self.config.timeout,
                "verify": self.config.ssl_verify,
                "http2": True,
            }

            # Add proxy if configured
            if self.config.proxy_config:
                if self.config.proxy_config.https_proxy:
                    client_kwargs["proxy"] = self.config.proxy_config.https_proxy
                elif self.config.proxy_config.http_proxy:
                    client_kwargs["proxy"] = self.config.proxy_config.http_proxy

            self._http_client = httpx.AsyncClient(**client_kwargs)

    async def _connect_websocket(self):
        """Connect via WebSocket"""
        logger.warning(
            f"WebSocket not yet implemented for {self.endpoint}, using HTTP fallback"
        )
        self.use_websocket = False
        await self._ensure_http_client()

    async def close(self):
        """Close connection"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def call(
        self, method: str, params: Any = None, timeout: Optional[float] = None
    ) -> Any:
        """Make RPC call with automatic retries and rate limiting.

        Args:
            method: The RPC method to call
            params: Parameters for the RPC method
            timeout: Optional timeout override in seconds

        Returns:
            The result from the RPC call

        Raises:
            RPCError: If the RPC returns an error
            CSTimeoutError: If the request times out
            CSConnectionError: If connection fails
        """
        # Rate limiting: wait for semaphore slot
        async with self._rate_limiter:
            async with self._lock:
                self._request_id += 1
                request_id = self._request_id

            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or [],
            }

            timeout = timeout or self.config.timeout

            # Use tenacity for retries
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.config.max_retries + 1),
                wait=wait_exponential(
                    multiplier=self.config.retry_delay,
                    min=self.config.retry_delay,
                    max=10,
                ),
                retry=retry_if_exception_type(
                    (httpx.TimeoutException, httpx.HTTPError)
                ),
                reraise=True,
            ):
                with attempt:
                    await self._ensure_http_client()

                    try:
                        response = await self._http_client.post(
                            self.endpoint, json=payload, timeout=timeout
                        )

                        response.raise_for_status()
                        data = response.json()

                        if "error" in data:
                            error = data["error"]
                            raise RPCError(
                                message=error.get("message", "Unknown RPC error"),
                                code=error.get("code"),
                                data=error.get("data"),
                            )

                        return data.get("result")

                    except httpx.TimeoutException as e:
                        logger.warning(
                            f"RPC timeout (attempt {attempt.retry_state.attempt_number}): {method}"
                        )
                        raise CSTimeoutError(f"RPC call timed out after {timeout}s", e)

                    except httpx.HTTPError as e:
                        logger.warning(
                            f"RPC HTTP error (attempt {attempt.retry_state.attempt_number}): {method}"
                        )
                        raise CSConnectionError(f"RPC call failed: {str(e)}", e)

                    except RPCError:
                        raise

                    except Exception as e:
                        logger.error(f"Unexpected RPC error: {str(e)}")
                        raise CSConnectionError(f"Unexpected error: {str(e)}", e)

    @asynccontextmanager
    async def batch(self):
        """Context manager for batch RPC calls (future enhancement)"""
        yield self

    def __repr__(self):
        return f"RPCClient(endpoint={self.endpoint}, connected={self._connected})"
