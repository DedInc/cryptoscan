"""
RPC client for CryptoScan.

Production-ready async RPC client with auto-reconnect and error handling.
"""

from __future__ import annotations

import asyncio
import logging
from types import TracebackType
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..core.config import UserConfig
from ..core.exceptions import (
    CSConnectionError,
    CSTimeoutError,
    RPCError,
    ValidationError,
)
from ..security import mask_url, validate_rpc_url
from .payloads import (
    build_batch_payload,
    build_single_payload,
    extract_batch_results,
    extract_single_result,
)

__all__ = ["RPCClient", "RPCResult"]

logger = logging.getLogger(__name__)

RPCResult = dict[str, Any] | list[Any] | str | int | float | bool | None


class RPCClient:
    """Async WebSocket/HTTP RPC client with automatic reconnection.

    Features: rate limiting via semaphore, automatic retries with
    exponential backoff, and HTTP/2 support.
    """

    def __init__(
        self,
        endpoint: str,
        user_config: UserConfig | None = None,
        use_websocket: bool = True,
        max_concurrent_requests: int = 10,
    ) -> None:
        if not validate_rpc_url(endpoint):
            raise ValidationError(f"Invalid or unsafe RPC URL: {endpoint}")
        self.endpoint = endpoint
        self.use_websocket = use_websocket and endpoint.startswith(("ws://", "wss://"))
        self.config = user_config or UserConfig()
        self._http_client: httpx.AsyncClient | None = None
        self._ws_client = None
        self._connected = False
        self._reconnect_attempts = 0
        self._request_id = 0
        self._lock: asyncio.Lock | None = None
        self._rate_limiter = asyncio.Semaphore(max_concurrent_requests)

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self) -> None:
        """Establish connection."""
        if self.use_websocket:
            await self._connect_websocket()
        else:
            await self._ensure_http_client()

    async def _ensure_http_client(self) -> None:
        """Ensure HTTP client is created."""
        if self._http_client is not None:
            return
        client_kwargs: dict[str, Any] = {
            "timeout": self.config.timeout,
            "verify": self.config.ssl_verify,
            "http2": True,
        }
        if self.config.proxy_config:
            proxy_url = (
                self.config.proxy_config.https_proxy
                or self.config.proxy_config.http_proxy
            )
            if proxy_url:
                proxy_url = self._apply_proxy_auth(proxy_url)
                client_kwargs["proxy"] = proxy_url
            if self.config.proxy_config.proxy_headers:
                client_kwargs["headers"] = self.config.proxy_config.proxy_headers
        self._http_client = httpx.AsyncClient(**client_kwargs)

    def _apply_proxy_auth(self, proxy_url: str) -> str:
        auth = self.config.proxy_config.proxy_auth if self.config.proxy_config else None
        if not auth or "@" in proxy_url.split("://", 1)[-1].split("/")[0]:
            return proxy_url
        parsed = urlparse(proxy_url)
        netloc = f"{auth}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))

    async def _connect_websocket(self) -> None:
        """Connect via WebSocket (currently falls back to HTTP)."""
        logger.warning(
            "WebSocket not yet implemented for %s, using HTTP fallback",
            mask_url(self.endpoint),
        )
        self.use_websocket = False
        await self._ensure_http_client()

    async def close(self) -> None:
        """Close connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def call(
        self,
        method: str,
        params: list | dict | None = None,
        timeout: float | None = None,
    ) -> RPCResult:
        """Make RPC call with automatic retries and rate limiting."""
        async with self._rate_limiter:
            async with self._get_lock():
                self._request_id += 1
                request_id = self._request_id
            payload = build_single_payload(request_id, method, params)
            timeout = timeout or self.config.timeout
            try:
                logger.debug("RPC call: %s", method)
                data = await self._make_http_request(payload, timeout)
                if not isinstance(data, dict):
                    raise CSConnectionError("Unexpected response format")
                return extract_single_result(data)
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                raise self._convert_http_error(e, method, timeout) from e
            except RPCError:
                raise
            except Exception as e:
                logger.error(f"Unexpected RPC error: {e}")
                raise CSConnectionError(f"Unexpected error: {e}", e) from e

    async def _make_http_request(
        self, payload: dict | list, timeout: float | None
    ) -> dict | list:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.config.max_retries + 1),
            wait=wait_exponential(
                multiplier=self.config.retry_delay, min=self.config.retry_delay, max=10
            ),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPError)),
            before_sleep=before_sleep_log(logger, logging.DEBUG),
            reraise=True,
        ):
            with attempt:
                await self._ensure_http_client()
                response = await self._http_client.post(
                    self.endpoint, json=payload, timeout=timeout
                )
                response.raise_for_status()
                return response.json()
        raise CSConnectionError("Request failed after all retries")

    async def batch(
        self,
        requests: list[tuple[str, list | dict | None]],
        timeout: float | None = None,
    ) -> list[RPCResult]:
        """Send multiple RPC calls as a single JSON-RPC 2.0 batch request."""
        async with self._rate_limiter:
            async with self._get_lock():
                base_id = self._request_id + 1
                self._request_id = base_id + len(requests) - 1
            payload = build_batch_payload(requests, base_id)
            timeout = timeout or self.config.timeout
            try:
                logger.debug("RPC batch: %d requests", len(requests))
                raw = await self._make_http_request(payload, timeout)
                if not isinstance(raw, list):
                    raise CSConnectionError("Batch response is not a list")
                return extract_batch_results(raw)
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                raise self._convert_http_error(e, "batch", timeout) from e
            except RPCError:
                raise
            except Exception as e:
                logger.error("Unexpected RPC batch error: %s", e)
                raise CSConnectionError(f"Unexpected error in batch: {e}", e) from e

    def _convert_http_error(
        self, error: httpx.HTTPError, context: str, timeout: float | None
    ) -> Exception:
        """Convert an httpx error to the appropriate CryptoScan exception."""
        if isinstance(error, httpx.TimeoutException):
            logger.error(
                "RPC timeout after %s retries: %s", self.config.max_retries, context
            )
            return CSTimeoutError(f"RPC call timed out after {timeout}s", error)
        logger.error(
            "RPC HTTP error after %s retries: %s", self.config.max_retries, context
        )
        return CSConnectionError(f"RPC call failed: {error.__class__.__name__}", error)

    async def __aenter__(self) -> RPCClient:
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

    def __repr__(self) -> str:
        return (
            f"RPCClient(endpoint={mask_url(self.endpoint)}, "
            f"connected={self._connected})"
        )
