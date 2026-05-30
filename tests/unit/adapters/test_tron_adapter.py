from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cryptoscan.adapters.tron_adapter import TRONGridAdapter
from cryptoscan.core.models import PaymentInfo, PaymentStatus
from cryptoscan.networks import NetworkConfig


@pytest.fixture
def tron_config() -> NetworkConfig:
    return NetworkConfig(
        name="tron",
        symbol="TRX",
        rpc_url="https://api.trongrid.io",
        decimals=6,
        chain_type="tron",
    )


def make_adapter(tron_config: NetworkConfig) -> TRONGridAdapter:
    with patch("cryptoscan.adapters.base.validate_rpc_url", return_value=True):
        adapter = TRONGridAdapter(
            rpc_url="https://api.trongrid.io",
            network_config=tron_config,
            max_retries=0,
            retry_delay=0,
        )
    adapter.http_client = AsyncMock()
    return adapter


def valid_tron_tx() -> dict:
    return {
        "txID": "tx123456",
        "raw_data": {
            "contract": [
                {
                    "parameter": {
                        "value": {
                            "amount": 5000000,
                            "to_address": "TXYZ",
                            "owner_address": "TABC",
                        }
                    }
                }
            ],
            "timestamp": 1700000000000,
        },
        "ret": [{"contractRet": "SUCCESS"}],
        "blockNumber": 55555,
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


class TestParseTronTx:
    def test_valid_tx(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        result = adapter._parse_tron_tx(valid_tron_tx())
        assert isinstance(result, PaymentInfo)
        assert result.transaction_id == "tx123456"
        assert result.amount == Decimal("5000000") / Decimal(10**6)
        assert result.amount == Decimal("5")
        assert result.to_address == "TXYZ"
        assert result.from_address == "TABC"
        assert result.block_height == 55555
        assert result.currency == "TRX"

    def test_confirmed_status(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        result = adapter._parse_tron_tx(valid_tron_tx())
        assert result.status == PaymentStatus.CONFIRMED

    def test_failed_status(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        tx = valid_tron_tx()
        tx["ret"] = [{"contractRet": "REVERT"}]
        result = adapter._parse_tron_tx(tx)
        assert result.status == PaymentStatus.FAILED

    def test_none_for_malformed_empty_contract(
        self, tron_config: NetworkConfig
    ) -> None:
        adapter = make_adapter(tron_config)
        tx = {"raw_data": {"contract": []}, "txID": "x"}
        result = adapter._parse_tron_tx(tx)
        assert result is None

    def test_none_for_wrong_types(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        tx = {
            "raw_data": {
                "contract": [{"parameter": {"value": {"amount": None}}}],
                "timestamp": 0,
            }
        }
        result = adapter._parse_tron_tx(tx)
        assert result is None


class TestGetTransactions:
    async def test_returns_parsed_list(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        adapter.http_client.get.return_value = mock_response(
            {"data": [valid_tron_tx(), valid_tron_tx()]}
        )
        result = await adapter.get_transactions("TAddr", limit=10)
        assert len(result) == 2
        assert all(isinstance(t, PaymentInfo) for t in result)

    async def test_limits_results(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        txs = [valid_tron_tx() for _ in range(20)]
        adapter.http_client.get.return_value = mock_response({"data": txs})
        result = await adapter.get_transactions("TAddr", limit=5)
        assert len(result) == 5

    async def test_empty_data(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        adapter.http_client.get.return_value = mock_response({"data": []})
        result = await adapter.get_transactions("TAddr")
        assert result == []


class TestGetTransaction:
    async def test_returns_payment_info(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        adapter.http_client.get.return_value = mock_response(valid_tron_tx())
        result = await adapter.get_transaction("txhash")
        assert isinstance(result, PaymentInfo)
        assert result.transaction_id == "tx123456"

    async def test_none_on_httpx_error(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        adapter.http_client.get.side_effect = httpx.HTTPError("fail")
        result = await adapter.get_transaction("txhash")
        assert result is None

    async def test_none_on_parse_error(self, tron_config: NetworkConfig) -> None:
        adapter = make_adapter(tron_config)
        bad_resp = {
            "raw_data": {
                "contract": [{"parameter": {"value": {"amount": None}}}],
                "timestamp": 0,
            }
        }
        adapter.http_client.get.return_value = mock_response(bad_resp)
        result = await adapter.get_transaction("txhash")
        assert result is None
