from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cryptoscan.core.config import UserConfig
from cryptoscan.core.exceptions import CSConnectionError, CSTimeoutError, RPCError
from cryptoscan.rpc.client import RPCClient


@pytest.fixture
def config() -> UserConfig:
    return UserConfig(timeout=1.0, max_retries=2, retry_delay=0.01)


@pytest.fixture
def rpc_client(config: UserConfig) -> RPCClient:
    return RPCClient("https://ethereum-rpc.publicnode.com", config)


def _setup_mock_http_client(
    rpc_client: RPCClient,
    response_or_exception: MagicMock | BaseException | list,
) -> MagicMock:
    mock_client = MagicMock()
    se = response_or_exception
    if isinstance(se, (BaseException, list)):
        mock_client.post = AsyncMock(side_effect=se)
    else:
        mock_client.post = AsyncMock(return_value=se)
    rpc_client._http_client = mock_client
    return mock_client


def _make_success_response(result: str = "0x123") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"result": result})
    return mock_resp


class TestRPCTimeoutRetry:
    async def test_timeout_raises_cstimeout_error(self, rpc_client: RPCClient) -> None:
        _setup_mock_http_client(rpc_client, httpx.TimeoutException("timeout"))

        with (
            patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock),
            pytest.raises(CSTimeoutError),
        ):
            await rpc_client.call("eth_blockNumber")

    async def test_timeout_retry_count_matches(self, rpc_client: RPCClient) -> None:
        mock_client = _setup_mock_http_client(
            rpc_client, httpx.TimeoutException("timeout")
        )

        with (
            patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock),
            pytest.raises(CSTimeoutError),
        ):
            await rpc_client.call("eth_blockNumber")

        expected_attempts = rpc_client.config.max_retries + 1
        assert mock_client.post.call_count == expected_attempts


class TestRPCHTTPErrorRetry:
    async def test_http_error_raises_cs_connection_error(
        self, rpc_client: RPCClient
    ) -> None:
        _setup_mock_http_client(rpc_client, httpx.ConnectError("refused"))

        with (
            patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock),
            pytest.raises(CSConnectionError),
        ):
            await rpc_client.call("eth_blockNumber")

    async def test_http_error_retry_count_matches(self, rpc_client: RPCClient) -> None:
        mock_client = _setup_mock_http_client(rpc_client, httpx.ConnectError("refused"))

        with (
            patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock),
            pytest.raises(CSConnectionError),
        ):
            await rpc_client.call("eth_blockNumber")

        expected_attempts = rpc_client.config.max_retries + 1
        assert mock_client.post.call_count == expected_attempts


class TestRPCSuccessfulCall:
    async def test_success_after_one_retry(self, rpc_client: RPCClient) -> None:
        success_resp = _make_success_response("0xabc")
        mock_client = _setup_mock_http_client(
            rpc_client,
            [httpx.TimeoutException("timeout"), success_resp],
        )

        with patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock):
            result = await rpc_client.call("eth_blockNumber")

        assert result == "0xabc"
        assert mock_client.post.call_count == 2

    async def test_immediate_success(self, rpc_client: RPCClient) -> None:
        success_resp = _make_success_response("0x42")
        _setup_mock_http_client(rpc_client, success_resp)

        with patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock):
            result = await rpc_client.call("eth_getBalance")

        assert result == "0x42"


class TestRPCErrorHandling:
    async def test_rpc_error_raised_on_error_response(
        self, rpc_client: RPCClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={
                "error": {
                    "message": "method not found",
                    "code": -32601,
                    "data": {"detail": "unsupported"},
                }
            }
        )
        _setup_mock_http_client(rpc_client, mock_resp)

        with (
            patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock),
            pytest.raises(RPCError) as exc_info,
        ):
            await rpc_client.call("eth_invalidMethod")

        assert exc_info.value.message == "method not found"
        assert exc_info.value.code == -32601
        assert exc_info.value.data == {"detail": "unsupported"}

    async def test_rpc_error_defaults_when_fields_missing(
        self, rpc_client: RPCClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"error": {}})
        _setup_mock_http_client(rpc_client, mock_resp)

        with (
            patch.object(rpc_client, "_ensure_http_client", new_callable=AsyncMock),
            pytest.raises(RPCError) as exc_info,
        ):
            await rpc_client.call("eth_call")

        assert exc_info.value.message == "Unknown RPC error"
        assert exc_info.value.code is None
        assert exc_info.value.data == {}
