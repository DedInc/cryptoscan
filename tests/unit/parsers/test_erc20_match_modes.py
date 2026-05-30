from __future__ import annotations

from decimal import Decimal

from cryptoscan.core.models import MatchMode, TokenConfig
from cryptoscan.networks import NetworkConfig
from cryptoscan.parsers.evm import EVMParser

from .test_erc20_parser import (  # noqa: F401 — registers `config` fixture
    BLOCK_NUMBER,
    TOKEN_CONTRACT,
    WALLET,
    _make_block,
    _make_native_tx,
    _make_receipt,
    _make_token_tx,
    _make_transfer_log,
    _mock_client,
    config,  # noqa: F401, F811
)


async def test_match_mode_any_returns_all(config: NetworkConfig) -> None:  # noqa: F811
    from .test_erc20_parser import TX_HASH

    tx1 = {**_make_native_tx(), "hash": TX_HASH + "1"}
    tx2 = {**_make_native_tx(), "hash": TX_HASH + "2"}
    block = _make_block([tx1, tx2])
    client = _mock_client(block)
    parser = EVMParser(client, config, "ETH")

    results = await parser.get_transactions(WALLET, 10, match_mode=MatchMode.ANY)
    assert len(results) == 2


async def test_match_mode_at_least_early_exit(config: NetworkConfig) -> None:  # noqa: F811
    block = _make_block([_make_native_tx(value=hex(2_000_000))])
    client = _mock_client(block)
    parser = EVMParser(client, config, "ETH")

    results = await parser.get_transactions(
        WALLET, 10, expected_amount=Decimal("1.0"), match_mode=MatchMode.AT_LEAST
    )
    assert len(results) == 1
    assert results[0].amount == Decimal("2.0")


async def test_match_mode_exact_does_not_early_return_on_mismatch(
    config: NetworkConfig,  # noqa: F811
) -> None:
    block = _make_block([_make_native_tx(value=hex(1_000_001))])
    client = _mock_client(block)
    parser = EVMParser(client, config, "ETH")

    results = await parser.get_transactions(
        WALLET, 10, expected_amount=Decimal(1_000_000), match_mode=MatchMode.EXACT
    )
    assert len(results) == 1
    assert results[0].amount != Decimal(1_000_000)


async def test_match_mode_at_least_with_token_config(
    ethereum_config: NetworkConfig,
) -> None:
    tc = TokenConfig(contract_address=TOKEN_CONTRACT, symbol="USDT", decimals=6)
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=15_000_000)])
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, ethereum_config, "ETH")

    results = await parser.get_transactions(
        WALLET,
        1,
        expected_amount=Decimal("10"),
        match_mode=MatchMode.AT_LEAST,
        token_contract=tc,
    )
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 1
    assert token_payments[0].amount == Decimal(15)
