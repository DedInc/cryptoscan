import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from cryptoscan.websocket.connection_manager import WebSocketConnectionManager
from cryptoscan.websocket.subscription_manager import (
    SubscriptionType,
    WebSocketSubscriptionManager,
)


@pytest.fixture
def mock_conn_mgr() -> MagicMock:
    mgr = MagicMock(spec=WebSocketConnectionManager)
    mgr.is_connected = MagicMock(return_value=True)
    mgr.send_message = AsyncMock()
    mgr.receive_message = AsyncMock(return_value='{"result": "0xabc123"}')
    mgr.connect = AsyncMock()
    return mgr


@pytest.fixture
def sub_mgr(mock_conn_mgr: MagicMock) -> WebSocketSubscriptionManager:
    return WebSocketSubscriptionManager(mock_conn_mgr)


def make_response(sub_id: str = "0xabc123") -> str:
    return json.dumps({"result": sub_id})


class TestSubscribeNewHeads:
    async def test_sends_correct_message(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        callback = AsyncMock()
        await sub_mgr.subscribe_new_heads(callback)
        sent = json.loads(mock_conn_mgr.send_message.call_args[0][0])
        assert sent["method"] == "eth_subscribe"
        assert sent["params"] == ["newHeads"]

    async def test_stores_callback(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        callback = AsyncMock()
        await sub_mgr.subscribe_new_heads(callback)
        assert "0xsub1" in sub_mgr._subscriptions
        assert sub_mgr._subscriptions["0xsub1"] is callback

    async def test_returns_subscription_id(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        result = await sub_mgr.subscribe_new_heads(AsyncMock())
        assert result == "0xsub1"

    async def test_registers_for_restoration(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        assert len(sub_mgr._subscription_registry) == 1
        assert (
            sub_mgr._subscription_registry[0].subscription_type
            == SubscriptionType.NEW_HEADS
        )


class TestSubscribeLogs:
    async def test_sends_with_addresses(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xlog1")
        callback = AsyncMock()
        await sub_mgr.subscribe_logs(["0xAddr1", "0xAddr2"], callback)
        sent = json.loads(mock_conn_mgr.send_message.call_args[0][0])
        assert sent["method"] == "eth_subscribe"
        assert sent["params"] == ["logs", {"address": ["0xAddr1", "0xAddr2"]}]

    async def test_stores_callback(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xlog1")
        callback = AsyncMock()
        await sub_mgr.subscribe_logs(["0xAddr1"], callback)
        assert sub_mgr._subscriptions["0xlog1"] is callback


class TestSubscribePendingTransactions:
    async def test_sends_pending_tx(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xpend1")
        callback = AsyncMock()
        await sub_mgr.subscribe_pending_transactions(callback)
        sent = json.loads(mock_conn_mgr.send_message.call_args[0][0])
        assert sent["method"] == "eth_subscribe"
        assert sent["params"] == ["newPendingTransactions"]

    async def test_stores_callback(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xpend1")
        callback = AsyncMock()
        await sub_mgr.subscribe_pending_transactions(callback)
        assert sub_mgr._subscriptions["0xpend1"] is callback


class TestUnsubscribe:
    async def test_sends_unsubscribe(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        await sub_mgr.unsubscribe("0xsub1")
        sent = json.loads(mock_conn_mgr.send_message.call_args[0][0])
        assert sent["method"] == "eth_unsubscribe"
        assert sent["params"] == ["0xsub1"]

    async def test_removes_from_active(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        assert "0xsub1" in sub_mgr._subscriptions
        await sub_mgr.unsubscribe("0xsub1")
        assert "0xsub1" not in sub_mgr._subscriptions

    async def test_noop_for_unknown(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        await sub_mgr.unsubscribe("0xnonexistent")
        mock_conn_mgr.send_message.assert_not_called()


class TestHandleSubscriptionMessage:
    async def test_dispatches_to_callback(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        callback = AsyncMock()
        await sub_mgr.subscribe_new_heads(callback)
        msg = {
            "method": "eth_subscription",
            "params": {"subscription": "0xsub1", "result": {"number": "0x1"}},
        }
        handled = await sub_mgr.handle_subscription_message(msg)
        assert handled is True
        callback.assert_awaited_once_with({"number": "0x1"})

    async def test_returns_false_unknown_sub(
        self, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        msg = {
            "method": "eth_subscription",
            "params": {"subscription": "0xunknown", "result": {}},
        }
        assert await sub_mgr.handle_subscription_message(msg) is False

    async def test_returns_false_wrong_method(
        self, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        msg = {"method": "other_method", "params": {}}
        assert await sub_mgr.handle_subscription_message(msg) is False

    async def test_sync_callback(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        results = []

        def sync_cb(data: dict) -> None:
            results.append(data)

        await sub_mgr.subscribe_new_heads(sync_cb)
        msg = {
            "method": "eth_subscription",
            "params": {"subscription": "0xsub1", "result": {"block": 1}},
        }
        handled = await sub_mgr.handle_subscription_message(msg)
        assert handled is True
        assert results == [{"block": 1}]


class TestClearMethods:
    async def test_clear_subscriptions_preserves_registry(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        assert len(sub_mgr._subscriptions) == 1
        assert len(sub_mgr._subscription_registry) == 1
        sub_mgr.clear_subscriptions()
        assert len(sub_mgr._subscriptions) == 0
        assert len(sub_mgr._subscription_registry) == 1

    async def test_clear_registry_clears_both(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        sub_mgr.clear_registry()
        assert len(sub_mgr._subscriptions) == 0
        assert len(sub_mgr._subscription_registry) == 0


class TestRestoreSubscriptions:
    async def test_restores_all(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        mock_conn_mgr.receive_message.return_value = make_response("0xsub2")
        await sub_mgr.subscribe_logs(["0xAddr"], AsyncMock())
        assert len(sub_mgr._subscription_registry) == 2
        mock_conn_mgr.receive_message.side_effect = [
            make_response("0xnew1"),
            make_response("0xnew2"),
        ]
        count = await sub_mgr.restore_subscriptions()
        assert count == 2

    async def test_returns_zero_when_empty(
        self, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        count = await sub_mgr.restore_subscriptions()
        assert count == 0

    async def test_failed_kept_in_registry(
        self, mock_conn_mgr: MagicMock, sub_mgr: WebSocketSubscriptionManager
    ) -> None:
        mock_conn_mgr.receive_message.return_value = make_response("0xsub1")
        await sub_mgr.subscribe_new_heads(AsyncMock())
        assert len(sub_mgr._subscription_registry) == 1
        mock_conn_mgr.send_message.side_effect = Exception("boom")
        count = await sub_mgr.restore_subscriptions()
        assert count == 0
        assert len(sub_mgr._subscription_registry) == 1
