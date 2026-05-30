from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cryptoscan.adapters.ton_adapter import TONCenterAdapter
from cryptoscan.core.models import PaymentInfo, PaymentStatus
from cryptoscan.networks import NetworkConfig


@pytest.fixture
def ton_config() -> NetworkConfig:
    return NetworkConfig(
        name="ton",
        symbol="TON",
        rpc_url="https://toncenter.com/api/v2/jsonRPC",
        decimals=9,
        chain_type="ton",
    )


def make_adapter(ton_config: NetworkConfig) -> TONCenterAdapter:
    with patch("cryptoscan.adapters.base.validate_rpc_url", return_value=True):
        adapter = TONCenterAdapter(
            rpc_url="https://toncenter.com/api/v2/jsonRPC",
            network_config=ton_config,
            max_retries=0,
            retry_delay=0,
        )
    adapter.http_client = AsyncMock()
    return adapter


def valid_ton_tx() -> dict:
    return {
        "transaction_id": {"hash": "abc123"},
        "in_msg": {
            "value": "1000000000",
            "source": "EQSourceAddr",
            "destination": "EQDestAddr",
        },
        "utime": 1700000000,
        "fee": "10000000",
    }


def mock_response(
    json_data: dict,
    content_type: str = "application/json",
    content_length: str = "1000",
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {
        "content-type": content_type,
        "content-length": str(content_length),
    }
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestParseTonTx:
    def test_valid_tx(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        tx = valid_ton_tx()
        result = adapter._parse_ton_tx(tx)
        assert isinstance(result, PaymentInfo)
        assert result.transaction_id == "abc123"
        assert result.from_address == "EQSourceAddr"
        assert result.to_address == "EQDestAddr"
        assert result.wallet_address == "EQDestAddr"
        assert result.currency == "TON"
        assert result.status == PaymentStatus.CONFIRMED
        assert result.confirmations == 1

    def test_amount_conversion(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        tx = valid_ton_tx()
        tx["in_msg"]["value"] = "5000000000"
        result = adapter._parse_ton_tx(tx)
        assert result.amount == Decimal("5000000000") / Decimal(10**9)
        assert result.amount == Decimal("5")

    def test_missing_in_msg(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        tx = {
            "transaction_id": {"hash": "abc"},
            "utime": 1700000000,
            "fee": "0",
        }
        result = adapter._parse_ton_tx(tx)
        assert isinstance(result, PaymentInfo)
        assert result.amount == Decimal("0")

    def test_none_for_bad_type(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        result = adapter._parse_ton_tx({"in_msg": {"value": "not_a_number"}})
        assert result is None

    def test_empty_in_msg_fields(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        tx = {
            "transaction_id": {"hash": "x"},
            "in_msg": {},
            "utime": 0,
            "fee": "0",
        }
        result = adapter._parse_ton_tx(tx)
        assert isinstance(result, PaymentInfo)
        assert result.amount == Decimal("0")
        assert result.from_address == ""
        assert result.to_address == ""


class TestGetTransactions:
    async def test_returns_list(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        adapter.http_client.post.return_value = mock_response(
            {"result": [valid_ton_tx()]}
        )
        result = await adapter.get_transactions("EQAddr123", limit=5)
        assert len(result) == 1
        assert isinstance(result[0], PaymentInfo)

    async def test_empty_no_result_key(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        adapter.http_client.post.return_value = mock_response({"ok": True})
        result = await adapter.get_transactions("EQAddr123")
        assert result == []

    async def test_raises_on_httpx_error(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        adapter.http_client.post.side_effect = httpx.HTTPError("fail")
        with pytest.raises(httpx.HTTPError):
            await adapter.get_transactions("EQAddr123")


class TestGetTransaction:
    async def test_returns_payment_info(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        adapter.http_client.post.return_value = mock_response(
            {"result": valid_ton_tx()}
        )
        result = await adapter.get_transaction("txhash123")
        assert isinstance(result, PaymentInfo)
        assert result.transaction_id == "abc123"

    async def test_none_no_result_key(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        adapter.http_client.post.return_value = mock_response({"ok": True})
        result = await adapter.get_transaction("txhash123")
        assert result is None

    async def test_none_on_httpx_error(self, ton_config: NetworkConfig) -> None:
        adapter = make_adapter(ton_config)
        adapter.http_client.post.side_effect = httpx.HTTPError("fail")
        result = await adapter.get_transaction("txhash123")
        assert result is None
