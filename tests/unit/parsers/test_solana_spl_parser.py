from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from cryptoscan.core.models import MatchMode, PaymentStatus, TokenConfig
from cryptoscan.networks import NetworkConfig
from cryptoscan.parsers.solana import SolanaParser

from .test_solana_spl_fixtures import (
    SENDER,
    SENDER_ATA,
    SIGNATURE,
    USDC_MINT,
    WALLET,
    WALLET_ATA,
    spl_incoming_tx,  # noqa: F401
    spl_no_incoming_tx,  # noqa: F401
    usdc_config,  # noqa: F401
)


@pytest.fixture
def parser(solana_config: NetworkConfig) -> SolanaParser:
    client = MagicMock()
    client.connect = AsyncMock()
    client.call = AsyncMock()
    return SolanaParser(client, solana_config, "SOL")


def test_spl_incoming_amount(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    result = parser._parse_spl_transfer(spl_incoming_tx, usdc_config, WALLET)
    assert result is not None
    assert result.amount == Decimal("10")
    assert result.currency == "USDC"
    assert result.token_contract == USDC_MINT
    assert result.to_address == WALLET
    assert result.status == PaymentStatus.CONFIRMED


def test_spl_sender_identified(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    result = parser._parse_spl_transfer(spl_incoming_tx, usdc_config, WALLET)
    assert result is not None
    assert result.from_address == SENDER


def test_spl_with_str_token_contract(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
) -> None:
    result = parser._parse_spl_transfer(spl_incoming_tx, USDC_MINT, WALLET)
    assert result is not None
    assert result.amount == Decimal("10000000") / Decimal(10**9)
    assert result.token_contract == USDC_MINT
    assert result.currency == "SOL"


def test_spl_failed_status(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    failed_tx = {
        **spl_incoming_tx,
        "meta": {**spl_incoming_tx["meta"], "err": "some error"},
    }
    result = parser._parse_spl_transfer(failed_tx, usdc_config, WALLET)
    assert result is not None
    assert result.status == PaymentStatus.FAILED


def test_spl_new_account_no_pre_balance(
    parser: SolanaParser,
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    new_account_tx = {
        "transaction": {
            "signatures": [SIGNATURE],
            "message": {"accountKeys": [SENDER, SENDER_ATA, WALLET_ATA]},
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [2000000000, 1000000, 0],
            "postBalances": [1995000000, 500000, 1500000],
            "preTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": SENDER,
                    "uiTokenAmount": {"amount": "1000000000", "decimals": 6},
                },
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": SENDER,
                    "uiTokenAmount": {"amount": "900000000", "decimals": 6},
                },
                {
                    "accountIndex": 2,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {"amount": "100000000", "decimals": 6},
                },
            ],
        },
        "slot": 260000003,
        "blockTime": 1700000180,
    }
    result = parser._parse_spl_transfer(new_account_tx, usdc_config, WALLET)
    assert result is not None
    assert result.amount == Decimal("100")


def test_spl_parse_with_token_prefers_spl(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    result = parser._parse_with_token(spl_incoming_tx, WALLET, usdc_config)
    assert result is not None
    assert result.token_contract == USDC_MINT


def test_spl_parse_with_token_falls_back_native(
    parser: SolanaParser,
    spl_no_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    result = parser._parse_with_token(spl_no_incoming_tx, WALLET, usdc_config)
    assert result is not None
    assert result.token_contract == ""
    assert result.currency == "SOL"


def test_spl_parse_with_token_none(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
) -> None:
    result = parser._parse_with_token(spl_incoming_tx, WALLET, None)
    assert result is not None
    assert result.token_contract == ""


@pytest.mark.asyncio
async def test_get_transactions_spl(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    parser.client.call = AsyncMock(
        side_effect=[
            [{"signature": SIGNATURE}],
            spl_incoming_tx,
        ]
    )
    result = await parser.get_transactions(
        WALLET, 10, Decimal("10"), MatchMode.EXACT, usdc_config
    )
    assert len(result) == 1
    assert result[0].amount == Decimal("10")
    assert result[0].token_contract == USDC_MINT


@pytest.mark.asyncio
async def test_get_transactions_native(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
) -> None:
    parser.client.call = AsyncMock(
        side_effect=[
            [{"signature": SIGNATURE}],
            spl_incoming_tx,
        ]
    )
    result = await parser.get_transactions(WALLET, 10)
    assert len(result) == 1
    assert result[0].token_contract == ""
    assert result[0].currency == "SOL"


@pytest.mark.asyncio
async def test_get_block_number(parser: SolanaParser) -> None:
    parser.client.call = AsyncMock(return_value=260000000)
    result = await parser.get_block_number()
    assert result == 260000000
    parser.client.call.assert_called_with("getSlot", [])


@pytest.mark.asyncio
async def test_get_block_for_payment_spl(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    block_data = {
        "transactions": [
            {
                "transaction": spl_incoming_tx["transaction"],
                "meta": spl_incoming_tx["meta"],
            }
        ],
        "blockTime": 1700000000,
    }
    parser.client.call = AsyncMock(return_value=block_data)
    result = await parser.get_block_for_payment(
        "260000000",
        WALLET,
        Decimal("10"),
        match_mode=MatchMode.EXACT,
        token_contract=usdc_config,
    )
    assert result is not None
    assert result.amount == Decimal("10")
    assert result.token_contract == USDC_MINT


@pytest.mark.asyncio
async def test_get_block_for_payment_no_match(
    parser: SolanaParser,
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    block_data = {
        "transactions": [
            {
                "transaction": spl_incoming_tx["transaction"],
                "meta": spl_incoming_tx["meta"],
            }
        ],
        "blockTime": 1700000000,
    }
    parser.client.call = AsyncMock(return_value=block_data)
    result = await parser.get_block_for_payment(
        "260000000",
        WALLET,
        Decimal("999"),
        match_mode=MatchMode.EXACT,
        token_contract=usdc_config,
    )
    assert result is None
