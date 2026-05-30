from unittest.mock import AsyncMock

import pytest

from cryptoscan.core.config import UserConfig
from cryptoscan.core.exceptions import CSConnectionError, ValidationError
from cryptoscan.websocket.connection_manager import WebSocketConnectionManager

TEST_WS_URL = "wss://ethereum-rpc.publicnode.com"


@pytest.fixture
def config() -> UserConfig:
    return UserConfig()


@pytest.fixture
def manager(config: UserConfig) -> WebSocketConnectionManager:
    return WebSocketConnectionManager(TEST_WS_URL, config)


class TestConstructor:
    def test_raises_validation_error_for_invalid_url(self, config: UserConfig) -> None:
        with pytest.raises(ValidationError, match="Invalid WebSocket URL"):
            WebSocketConnectionManager("http://invalid.com", config)

    def test_raises_validation_error_for_empty_url(self, config: UserConfig) -> None:
        with pytest.raises(ValidationError):
            WebSocketConnectionManager("", config)

    def test_raises_validation_error_for_no_scheme(self, config: UserConfig) -> None:
        with pytest.raises(ValidationError):
            WebSocketConnectionManager("not-a-url", config)

    def test_valid_ws_url_accepted(self, config: UserConfig) -> None:
        mgr = WebSocketConnectionManager(TEST_WS_URL, config)
        assert mgr.ws_url == TEST_WS_URL


class TestSendMessage:
    async def test_raises_connection_error_when_not_connected(
        self, manager: WebSocketConnectionManager
    ) -> None:
        with pytest.raises(CSConnectionError):
            await manager.send_message("test message")

    async def test_raises_connection_error_when_ws_is_none(
        self, manager: WebSocketConnectionManager
    ) -> None:
        manager._connected = False
        manager._ws = None
        with pytest.raises(CSConnectionError):
            await manager.send_message("test")


class TestReceiveMessage:
    async def test_raises_connection_error_when_not_connected(
        self, manager: WebSocketConnectionManager
    ) -> None:
        with pytest.raises(CSConnectionError):
            await manager.receive_message()

    async def test_raises_connection_error_with_timeout(
        self, manager: WebSocketConnectionManager
    ) -> None:
        manager._connected = False
        manager._ws = None
        with pytest.raises(CSConnectionError):
            await manager.receive_message(timeout=5.0)


class TestInitialState:
    def test_is_connected_returns_false_initially(
        self, manager: WebSocketConnectionManager
    ) -> None:
        assert manager.is_connected() is False

    def test_is_running_returns_false_initially(
        self, manager: WebSocketConnectionManager
    ) -> None:
        assert manager.is_running() is False

    def test_set_running_true(self, manager: WebSocketConnectionManager) -> None:
        manager.set_running(True)
        assert manager.is_running() is True

    def test_set_running_false(self, manager: WebSocketConnectionManager) -> None:
        manager.set_running(True)
        manager.set_running(False)
        assert manager.is_running() is False


class TestClose:
    async def test_close_sets_connected_false(
        self, manager: WebSocketConnectionManager
    ) -> None:
        manager._connected = True
        manager._ws = AsyncMock()
        await manager.close()
        assert manager._connected is False

    async def test_close_sets_running_false(
        self, manager: WebSocketConnectionManager
    ) -> None:
        manager._running = True
        manager._ws = AsyncMock()
        await manager.close()
        assert manager._running is False

    async def test_close_calls_ws_close(
        self, manager: WebSocketConnectionManager
    ) -> None:
        manager._ws = AsyncMock()
        await manager.close()
        manager._ws.close.assert_awaited_once()

    async def test_close_no_ws_does_not_raise(
        self, manager: WebSocketConnectionManager
    ) -> None:
        manager._ws = None
        await manager.close()
        assert manager._connected is False
