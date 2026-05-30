from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from cryptoscan.core.config import UserConfig
from cryptoscan.core.models import MatchMode, TokenConfig
from cryptoscan.networks import NetworkConfig
from cryptoscan.parsers.evm import EVMParser
from cryptoscan.parsers.evm_tokens import ERC20_TRANSFER_TOPIC

WALLET = "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"
TOKEN_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
FROM_ADDR = "0x1234567890123456789012345678901234567890"
WALLET_PADDED = "0x" + "0" * 24 + WALLET.lower()[2:]
FROM_PADDED = "0x" + "0" * 24 + FROM_ADDR[2:]
TX_HASH = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
BLOCK_NUMBER = 12345678
EMPTY_BLOCK = {
    "number": hex(BLOCK_NUMBER),
    "timestamp": "0x5f5e100",
    "transactions": [],
}


def _make_block(block_txs: list[dict]) -> dict:
    return {
        "number": hex(BLOCK_NUMBER),
        "timestamp": "0x5f5e100",
        "transactions": block_txs,
    }


def _make_native_tx(to: str = WALLET, value: str = "0xde0b6b3a7640000") -> dict:
    return {
        "hash": TX_HASH,
        "from": FROM_ADDR,
        "to": to,
        "value": value,
        "blockNumber": hex(BLOCK_NUMBER),
    }


def _make_token_tx(to_contract: str = TOKEN_CONTRACT) -> dict:
    return {
        "hash": TX_HASH,
        "from": FROM_ADDR,
        "to": to_contract,
        "value": "0x0",
        "blockNumber": hex(BLOCK_NUMBER),
    }


def _make_receipt(logs: list[dict] | None = None, status: str = "0x1") -> dict:
    return {"status": status, "logs": logs or []}


def _make_transfer_log(
    from_addr: str = FROM_ADDR,
    to_addr: str = WALLET,
    amount_raw: int = 1_000_000,
    address: str = TOKEN_CONTRACT,
) -> dict:
    return {
        "address": address,
        "topics": [
            ERC20_TRANSFER_TOPIC,
            "0x" + "0" * 24 + from_addr[2:],
            "0x" + "0" * 24 + to_addr[2:],
        ],
        "data": hex(amount_raw),
    }


def _mock_client(target_block: dict, receipt: dict | None = None) -> AsyncMock:
    """Create a mock client that returns target_block once, then empty blocks."""
    call_state = {"block_calls": 0}

    async def mock_call(
        method: str, _params: dict | None = None, *_a: object, **_kw: object
    ) -> dict | str | None:
        if method == "eth_blockNumber":
            return hex(BLOCK_NUMBER + 10)
        if method == "eth_getBlockByNumber":
            call_state["block_calls"] += 1
            if call_state["block_calls"] == 1:
                return target_block
            return EMPTY_BLOCK
        if method == "eth_getTransactionReceipt":
            return receipt
        return None

    client = MagicMock()
    client.connect = AsyncMock()
    client.call = mock_call
    client.config = UserConfig()
    return client


@pytest.fixture
def config() -> NetworkConfig:
    return NetworkConfig(
        name="ethereum",
        symbol="USDT",
        rpc_url="https://rpc.test",
        ws_url=None,
        address_pattern=r"^0x[a-fA-F0-9]{40}$",
        decimals=6,
        chain_type="evm",
    )


@pytest.fixture
def parser(config: NetworkConfig) -> EVMParser:
    client = MagicMock()
    client.connect = AsyncMock()
    client.call = AsyncMock()
    return EVMParser(client, config, "USDT")


async def test_native_transfer_matched(config: NetworkConfig) -> None:
    block = _make_block([_make_native_tx()])
    client = _mock_client(block)
    parser = EVMParser(client, config, "ETH")

    results = await parser.get_transactions(WALLET, 1)
    assert len(results) == 1
    assert results[0].to_address == WALLET


async def test_get_block_for_payment_token(config: NetworkConfig) -> None:
    block = _make_block([_make_token_tx()])
    block["hash"] = "0xblockhash"
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=1_000_000)])

    parser = EVMParser(MagicMock(), config, "USDT")
    parser.client.connect = AsyncMock()

    async def mock_call(
        method: str, _params: dict | None = None, *_a: object, **_kw: object
    ) -> dict | str | None:
        if method == "eth_getBlockByHash":
            return block
        if method == "eth_blockNumber":
            return hex(BLOCK_NUMBER)
        if method == "eth_getTransactionReceipt":
            return receipt
        return None

    parser.client.call = mock_call

    result = await parser.get_block_for_payment(
        "0xblockhash",
        WALLET,
        None,
        match_mode=MatchMode.ANY,
        token_contract=TOKEN_CONTRACT,
    )
    assert result is not None
    assert result.amount == Decimal(1)
    assert result.token_contract == TOKEN_CONTRACT


async def test_get_block_for_payment_native_at_least(config: NetworkConfig) -> None:
    block = _make_block([_make_native_tx(value=hex(5_000_000))])
    block["hash"] = "0xblockhash"

    parser = EVMParser(MagicMock(), config, "ETH")
    parser.client.connect = AsyncMock()

    async def mock_call(
        method: str, _params: dict | None = None, *_a: object, **_kw: object
    ) -> dict | str | None:
        if method == "eth_getBlockByHash":
            return block
        if method == "eth_blockNumber":
            return hex(BLOCK_NUMBER)
        return None

    parser.client.call = mock_call

    result = await parser.get_block_for_payment(
        "0xblockhash",
        WALLET,
        Decimal("3.0"),
        match_mode=MatchMode.AT_LEAST,
    )
    assert result is not None
    assert result.amount == Decimal("5.0")


async def test_get_block_for_payment_with_token_config(
    ethereum_config: NetworkConfig,
) -> None:
    tc = TokenConfig(contract_address=TOKEN_CONTRACT, symbol="USDC", decimals=6)
    block = _make_block([_make_token_tx()])
    block["hash"] = "0xblockhash"
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=25_000_000)])

    parser = EVMParser(MagicMock(), ethereum_config, "ETH")
    parser.client.connect = AsyncMock()

    async def mock_call(
        method: str, _params: dict | None = None, *_a: object, **_kw: object
    ) -> dict | str | None:
        if method == "eth_getBlockByHash":
            return block
        if method == "eth_blockNumber":
            return hex(BLOCK_NUMBER)
        if method == "eth_getTransactionReceipt":
            return receipt
        return None

    parser.client.call = mock_call

    result = await parser.get_block_for_payment(
        "0xblockhash",
        WALLET,
        Decimal("25"),
        match_mode=MatchMode.EXACT,
        token_contract=tc,
    )
    assert result is not None
    assert result.amount == Decimal(25)
    assert result.currency == "USDC"
    assert result.token_contract == TOKEN_CONTRACT
