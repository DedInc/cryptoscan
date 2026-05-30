from __future__ import annotations

from cryptoscan.core.models import TokenConfig
from cryptoscan.parsers.solana import SolanaParser

from .test_solana_spl_fixtures import (
    SIGNATURE,
    USDC_MINT,
    WALLET,
    WALLET_ATA,
    spl_incoming_tx,  # noqa: F401
    spl_no_incoming_tx,  # noqa: F401
    usdc_config,  # noqa: F401
)
from .test_solana_spl_parser import parser  # noqa: F401, F811


def test_spl_incoming_no_match_outgoing(
    parser: SolanaParser,  # noqa: F811
    spl_no_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    result = parser._parse_spl_transfer(spl_no_incoming_tx, usdc_config, WALLET)
    assert result is None


def test_spl_wrong_mint(
    parser: SolanaParser,  # noqa: F811
    spl_incoming_tx: dict,  # noqa: F811
) -> None:
    other_mint = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    result = parser._parse_spl_transfer(spl_incoming_tx, other_mint, WALLET)
    assert result is None


def test_spl_wrong_owner(
    parser: SolanaParser,  # noqa: F811
    spl_incoming_tx: dict,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    random_wallet = "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"
    result = parser._parse_spl_transfer(spl_incoming_tx, usdc_config, random_wallet)
    assert result is None


def test_spl_empty_balances(
    parser: SolanaParser,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    empty_tx = {
        "transaction": {
            "signatures": [SIGNATURE],
            "message": {"accountKeys": [WALLET]},
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [1000000000],
            "postBalances": [995000000],
            "preTokenBalances": [],
            "postTokenBalances": [],
        },
        "slot": 260000002,
        "blockTime": 1700000120,
    }
    result = parser._parse_spl_transfer(empty_tx, usdc_config, WALLET)
    assert result is None


def test_spl_no_meta(
    parser: SolanaParser,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    no_meta_tx = {
        "transaction": {
            "signatures": [SIGNATURE],
            "message": {"accountKeys": [WALLET]},
        },
        "meta": None,
    }
    result = parser._parse_spl_transfer(no_meta_tx, usdc_config, WALLET)
    assert result is None


def test_spl_zero_delta_skipped(
    parser: SolanaParser,  # noqa: F811
    usdc_config: TokenConfig,  # noqa: F811
) -> None:
    zero_delta_tx = {
        "transaction": {
            "signatures": [SIGNATURE],
            "message": {"accountKeys": [WALLET, WALLET_ATA]},
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [2000000000, 1000000],
            "postBalances": [1995000000, 1000000],
            "preTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {"amount": "500000", "decimals": 6},
                },
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {"amount": "500000", "decimals": 6},
                },
            ],
        },
        "slot": 260000004,
        "blockTime": 1700000240,
    }
    result = parser._parse_spl_transfer(zero_delta_tx, usdc_config, WALLET)
    assert result is None
