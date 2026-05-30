from __future__ import annotations

import pytest

from cryptoscan.core.models import TokenConfig

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WALLET = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
SENDER = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
SENDER_ATA = "4Nd1mZUmhYMkbkK7G1yKqR4sJxN86F3YjZtBvVwVnMfC"
WALLET_ATA = "F2qzBwL3q7X5mVYr8Pj9K3hN1WxT6b4ZaGqD2jC8vMnS"
SIGNATURE = (
    "5KtPn1LGuxhFiwjxErkxTt7Xkt7XtLVYUBe6Cn33ej7A"
    "TNQyXgzExvMGMKYz6D7xysgVW7bBTwLxCqzqzqzqz"
)


@pytest.fixture
def usdc_config() -> TokenConfig:
    return TokenConfig(contract_address=USDC_MINT, symbol="USDC", decimals=6)


@pytest.fixture
def spl_incoming_tx() -> dict:
    return {
        "transaction": {
            "signatures": [SIGNATURE],
            "message": {
                "accountKeys": [SENDER, SENDER_ATA, WALLET_ATA],
            },
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [2000000000, 1000000, 1000000],
            "postBalances": [1995000000, 500000, 1500000],
            "preTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": SENDER,
                    "uiTokenAmount": {
                        "amount": "1000000000",
                        "decimals": 6,
                        "uiAmount": 1000.0,
                        "uiAmountString": "1000",
                    },
                },
                {
                    "accountIndex": 2,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {
                        "amount": "500000",
                        "decimals": 6,
                        "uiAmount": 0.5,
                        "uiAmountString": "0.5",
                    },
                },
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": SENDER,
                    "uiTokenAmount": {
                        "amount": "990000000",
                        "decimals": 6,
                        "uiAmount": 990.0,
                        "uiAmountString": "990",
                    },
                },
                {
                    "accountIndex": 2,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {
                        "amount": "10500000",
                        "decimals": 6,
                        "uiAmount": 10.5,
                        "uiAmountString": "10.5",
                    },
                },
            ],
        },
        "slot": 260000000,
        "blockTime": 1700000000,
    }


@pytest.fixture
def spl_no_incoming_tx() -> dict:
    return {
        "transaction": {
            "signatures": [SIGNATURE],
            "message": {"accountKeys": [WALLET, WALLET_ATA, SENDER_ATA]},
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [2000000000, 1000000, 1000000],
            "postBalances": [1995000000, 500000, 1500000],
            "preTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {
                        "amount": "10500000",
                        "decimals": 6,
                        "uiAmount": 10.5,
                        "uiAmountString": "10.5",
                    },
                },
                {
                    "accountIndex": 2,
                    "mint": USDC_MINT,
                    "owner": SENDER,
                    "uiTokenAmount": {
                        "amount": "990000000",
                        "decimals": 6,
                        "uiAmount": 990.0,
                        "uiAmountString": "990",
                    },
                },
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 1,
                    "mint": USDC_MINT,
                    "owner": WALLET,
                    "uiTokenAmount": {
                        "amount": "500000",
                        "decimals": 6,
                        "uiAmount": 0.5,
                        "uiAmountString": "0.5",
                    },
                },
                {
                    "accountIndex": 2,
                    "mint": USDC_MINT,
                    "owner": SENDER,
                    "uiTokenAmount": {
                        "amount": "1000000000",
                        "decimals": 6,
                        "uiAmount": 1000.0,
                        "uiAmountString": "1000",
                    },
                },
            ],
        },
        "slot": 260000001,
        "blockTime": 1700000060,
    }
