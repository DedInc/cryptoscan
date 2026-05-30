import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cryptoscan.websocket.connection_manager import WebSocketConnectionManager
from cryptoscan.websocket.message_processor import (
    MAX_MESSAGE_SIZE,
    WebSocketMessageProcessor,
)
from cryptoscan.websocket.subscription_manager import WebSocketSubscriptionManager


@pytest.fixture
def mock_conn_mgr() -> MagicMock:
    mgr = MagicMock(spec=WebSocketConnectionManager)
    mgr.is_running = MagicMock(return_value=True)
    mgr.is_connected = MagicMock(return_value=True)
    mgr.set_running = MagicMock()
    config = MagicMock()
    config.ws_ping_timeout = 10
    mgr.config = config
    mgr.reconnect = AsyncMock(return_value=True)
    return mgr


@pytest.fixture
def mock_sub_mgr() -> AsyncMock:
    mgr = AsyncMock(spec=WebSocketSubscriptionManager)
    mgr.handle_subscription_message = AsyncMock(return_value=True)
    mgr.clear_subscriptions = MagicMock()
    mgr.restore_subscriptions = AsyncMock(return_value=1)
    return mgr


@pytest.fixture
def processor(
    mock_conn_mgr: MagicMock, mock_sub_mgr: AsyncMock
) -> WebSocketMessageProcessor:
    return WebSocketMessageProcessor(mock_conn_mgr, mock_sub_mgr)


class TestProcessMessage:
    async def test_dispatches_json(
        self, processor: WebSocketMessageProcessor, mock_sub_mgr: AsyncMock
    ) -> None:
        msg = json.dumps({"method": "eth_subscription", "params": {}})
        await processor._process_message(msg)
        mock_sub_mgr.handle_subscription_message.assert_awaited_once()

    async def test_warns_oversized(
        self, processor: WebSocketMessageProcessor, mock_sub_mgr: AsyncMock
    ) -> None:
        msg = "x" * (MAX_MESSAGE_SIZE + 1)
        await processor._process_message(msg)
        mock_sub_mgr.handle_subscription_message.assert_not_awaited()

    async def test_handles_invalid_json(
        self, processor: WebSocketMessageProcessor, mock_sub_mgr: AsyncMock
    ) -> None:
        await processor._process_message("not valid json{{{")
        mock_sub_mgr.handle_subscription_message.assert_not_awaited()

    async def test_unhandled_message(
        self, processor: WebSocketMessageProcessor, mock_sub_mgr: AsyncMock
    ) -> None:
        mock_sub_mgr.handle_subscription_message.return_value = False
        msg = json.dumps({"method": "unknown"})
        await processor._process_message(msg)
        mock_sub_mgr.handle_subscription_message.assert_awaited_once()


class TestStop:
    def test_sets_running_false(
        self, processor: WebSocketMessageProcessor, mock_conn_mgr: MagicMock
    ) -> None:
        processor.stop()
        mock_conn_mgr.set_running.assert_called_once_with(False)


class TestHandleConnectionError:
    async def test_non_websocket_returns_true(
        self, processor: WebSocketMessageProcessor
    ) -> None:
        with patch(
            "cryptoscan.websocket.message_processor.WEBSOCKETS_AVAILABLE", False
        ):
            result = await processor._handle_connection_error(ValueError("test"))
            assert result is True

    async def test_non_websocket_sleeps(
        self, processor: WebSocketMessageProcessor
    ) -> None:
        with (
            patch("cryptoscan.websocket.message_processor.WEBSOCKETS_AVAILABLE", False),
            patch(
                "cryptoscan.websocket.message_processor.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            await processor._handle_connection_error(RuntimeError("test"))
            mock_sleep.assert_awaited_once_with(0.5)

    async def test_websocket_closed_triggers_reconnect(
        self,
        processor: WebSocketMessageProcessor,
        mock_conn_mgr: MagicMock,
        mock_sub_mgr: AsyncMock,
    ) -> None:
        mock_ws = MagicMock()
        mock_ws.ConnectionClosed = type("ConnectionClosed", (Exception,), {})
        mock_ws.exceptions = MagicMock()
        mock_ws.exceptions.ConnectionClosed = mock_ws.ConnectionClosed
        error = mock_ws.ConnectionClosed("closed")
        with (
            patch("cryptoscan.websocket.message_processor.WEBSOCKETS_AVAILABLE", True),
            patch("cryptoscan.websocket.message_processor.websockets", mock_ws),
        ):
            result = await processor._handle_connection_error(error)
        assert result is True
        mock_sub_mgr.clear_subscriptions.assert_called_once()
        mock_conn_mgr.reconnect.assert_awaited_once()
        mock_sub_mgr.restore_subscriptions.assert_awaited_once()

    async def test_websocket_closed_reconnect_fails(
        self,
        processor: WebSocketMessageProcessor,
        mock_conn_mgr: MagicMock,
    ) -> None:
        mock_ws = MagicMock()
        mock_ws.ConnectionClosed = type("ConnectionClosed", (Exception,), {})
        mock_ws.exceptions = MagicMock()
        mock_ws.exceptions.ConnectionClosed = mock_ws.ConnectionClosed
        error = mock_ws.ConnectionClosed("closed")
        mock_conn_mgr.reconnect = AsyncMock(return_value=False)
        with (
            patch("cryptoscan.websocket.message_processor.WEBSOCKETS_AVAILABLE", True),
            patch("cryptoscan.websocket.message_processor.websockets", mock_ws),
        ):
            result = await processor._handle_connection_error(error)
        assert result is False
